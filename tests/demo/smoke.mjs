// End-to-end smoke test for the Pyodide demo at docs/demo/.
//
// Exercises the real Pyodide runtime against either:
//   - the live deployed URL (default): https://jordannewell.github.io/crypto-key-classifier/
//   - a local server via BASE_URL env var (e.g. http://127.0.0.1:8000/)
//
// Run locally:
//   cd tests/demo && npm install && npx playwright install chromium
//   BASE_URL=http://127.0.0.1:8000/ npm run smoke
//
// Exits non-zero on any failure so CI can detect breakage.

import { chromium } from "playwright";

const BASE_URL =
  process.env.BASE_URL || "https://jordannewell.github.io/crypto-key-classifier/";
const BOOT_TIMEOUT_MS = 60_000;
const CLASSIFY_TIMEOUT_MS = 10_000;

// ---------------------------------------------------------------------------
// Tiny test harness — no @playwright/test dep, just structured reporting.
// ---------------------------------------------------------------------------
const results = [];
function record(name, ok, detail) {
  results.push({ name, ok, detail });
  const tag = ok ? "PASS" : "FAIL";
  console.log(`[${tag}] ${name}${detail ? " :: " + detail : ""}`);
}

// Cases that exercise the example dropdown (shared classify flow).
const EXAMPLE_CASES = [
  { label: "BTC address (bech32)", minCards: 1 },
  { label: "ETH address (EIP-55 checksum)", minCards: 1 },
  { label: "Solana pubkey (base58 ed25519)", minCards: 1 },
  // ATOM is the cross-chain headline — expect many alternates.
  { label: "Cosmos ATOM address (20-chain HRP swap)", minCards: 1, minAlts: 15 },
  { label: "Corrupted BTC address (whitespace repair)", minCards: 1 },
  { label: "BIP-39 mnemonic (12 words, test vector 1)", minCards: 1, expectMaskedKey: true },
];

async function classifyExample(page, label) {
  await page.selectOption("#example-select", { label });
  await page.click("#classify-btn");
  await page.waitForFunction(
    () =>
      document.querySelectorAll(".match-card").length > 0 ||
      document.querySelector(".results__empty"),
    { timeout: CLASSIFY_TIMEOUT_MS }
  );
  return await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll(".match-card")).map((c) => ({
      chain: c.querySelector(".match-card__chain")?.textContent?.trim() ?? null,
      altCount: c.querySelectorAll(".match-card__alt").length,
      hasTrace: !!c.querySelector(".match-card__trace"),
      keyMasked:
        c.querySelector(".match-card__key")?.dataset?.sensitive === "1",
    }));
    const empty = document
      .querySelector(".results__empty")
      ?.textContent?.trim();
    return { cards, empty };
  });
}

async function boot(page) {
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: 60_000 });
  // Loader element gets `loader--hidden` once Pyodide is ready + classify wired.
  await page.waitForFunction(
    () =>
      document
        .getElementById("loader")
        ?.classList.contains("loader--hidden"),
    { timeout: BOOT_TIMEOUT_MS }
  );
  // Classify button is disabled until boot completes — belt and suspenders.
  await page.waitForSelector("#classify-btn:not([disabled])", { timeout: 10_000 });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 900 },
});

const pageErrors = [];
const failedReqs = [];

try {
  const page = await context.newPage();

  // Track uncaught errors + failed asset requests. Pyodide CDN failures are OK
  // if the page still boots (we verify boot separately), so we don't fail on
  // individual request failures — only on aggregate pageerror count at the end.
  page.on("pageerror", (err) => {
    pageErrors.push(err.message);
  });
  page.on("response", (res) => {
    const url = res.url();
    // Only track failures for the page's own origin (ignore third-party CDN).
    if (res.status() >= 400 && url.startsWith(BASE_URL)) {
      failedReqs.push({ url, status: res.status() });
    }
  });
  page.on("requestfailed", (req) => {
    const url = req.url();
    if (url.startsWith(BASE_URL)) {
      failedReqs.push({ url, failure: req.failure()?.errorText });
    }
  });

  // -----------------------------------------------------------------------
  // Boot
  // -----------------------------------------------------------------------
  try {
    const t0 = Date.now();
    await boot(page);
    record(
      "page boots within 60s",
      true,
      `boot in ${((Date.now() - t0) / 1000).toFixed(1)}s`
    );
  } catch (err) {
    record("page boots within 60s", false, String(err.message || err));
    // Nothing else can run if boot failed.
    throw err;
  }

  // -----------------------------------------------------------------------
  // Example dropdown cases
  // -----------------------------------------------------------------------
  for (const c of EXAMPLE_CASES) {
    try {
      const { cards, empty } = await classifyExample(page, c.label);

      if (c.expectMaskedKey) {
        const masked = cards.every((card) => card.keyMasked);
        record(
          `${c.label} — key masked (data-sensitive="1")`,
          cards.length > 0 && masked,
          cards.length > 0
            ? masked
              ? "all masked"
              : "NOT masked"
            : "no cards"
        );
      }

      if (c.minAlts !== undefined) {
        const maxAlts = Math.max(0, ...cards.map((card) => card.altCount));
        record(
          `${c.label} — ≥${c.minAlts} cross-chain alternates`,
          maxAlts >= c.minAlts,
          `got ${maxAlts}`
        );
      }

      record(
        `${c.label} — classifies`,
        cards.length >= c.minCards,
        cards.length > 0
          ? `${cards.length} card(s), first=${cards[0].chain}`
          : `empty="${empty?.slice(0, 80) ?? ""}"`
      );
    } catch (err) {
      record(`${c.label} — classifies`, false, String(err.message || err));
    }
  }

  // -----------------------------------------------------------------------
  // Repair trace toggle: ON shows .match-card__trace, OFF doesn't
  // -----------------------------------------------------------------------
  try {
    // OFF first (default state after prior cases may have toggled it).
    await page.uncheck("#explain-toggle");
    const offResult = await classifyExample(
      page,
      "Corrupted BTC address (whitespace repair)"
    );
    const traceOffCount = offResult.cards.filter((c) => c.hasTrace).length;

    await page.check("#explain-toggle");
    const onResult = await classifyExample(
      page,
      "Corrupted BTC address (whitespace repair)"
    );
    const traceOnCount = onResult.cards.filter((c) => c.hasTrace).length;

    record(
      "repair trace OFF hides .match-card__trace",
      traceOffCount === 0,
      `${traceOffCount} card(s) with trace`
    );
    record(
      "repair trace ON shows .match-card__trace",
      traceOnCount >= 1,
      `${traceOnCount} card(s) with trace`
    );

    // Reset for following cases.
    await page.uncheck("#explain-toggle");
  } catch (err) {
    record("repair trace toggle", false, String(err.message || err));
  }

  // -----------------------------------------------------------------------
  // No-match input
  // -----------------------------------------------------------------------
  try {
    await page.fill("#key-input", "hello world this is not a key");
    await page.click("#classify-btn");
    await page.waitForFunction(
      () => !!document.querySelector(".results__empty"),
      { timeout: CLASSIFY_TIMEOUT_MS }
    );
    const emptyText = await page.evaluate(
      () =>
        document
          .querySelector(".results__empty")
          ?.textContent?.trim()
          ?.slice(0, 120) ?? ""
    );
    const matched = /no classifier matched/i.test(emptyText);
    record(
      "no-match input shows 'No classifier matched'",
      matched,
      `text="${emptyText}"`
    );
  } catch (err) {
    record(
      "no-match input shows 'No classifier matched'",
      false,
      String(err.message || err)
    );
  }

  // -----------------------------------------------------------------------
  // Page health: zero pageerrors, zero failed same-origin requests
  // -----------------------------------------------------------------------
  record(
    "zero pageerror events",
    pageErrors.length === 0,
    pageErrors.length === 0
      ? ""
      : pageErrors.slice(0, 3).join(" | ").slice(0, 200)
  );
  record(
    "zero failed same-origin requests",
    failedReqs.length === 0,
    failedReqs.length === 0
      ? ""
      : JSON.stringify(failedReqs.slice(0, 3))
  );
} finally {
  await context.close();
  await browser.close();
}

// ---------------------------------------------------------------------------
// Summary + exit code
// ---------------------------------------------------------------------------
const passed = results.filter((r) => r.ok).length;
const failed = results.filter((r) => !r.ok).length;
console.log("");
console.log(`Smoke summary: ${passed} passed, ${failed} failed (of ${results.length})`);

if (failed > 0) {
  console.log("\nFailed cases:");
  for (const r of results.filter((r) => !r.ok)) {
    console.log(`  - ${r.name}${r.detail ? " :: " + r.detail : ""}`);
  }
  process.exit(1);
}
process.exit(0);
