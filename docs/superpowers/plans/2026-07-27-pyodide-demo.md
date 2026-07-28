# crypto-key-classifier Pyodide Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a single-page Pyodide-powered demo of `crypto-key-classifier` to `https://jordannewell.github.io/crypto-key-classifier/`.

**Architecture:** Static three-file site (`index.html` + `app.js` + `styles.css`) plus `examples.json`. JS loads Pyodide from jsdelivr, installs `crypto-key-classifier==0.6.1` via `micropip`, and calls `ckc.pipeline.classify` client-side. GitHub Actions deploys `docs/demo/` to Pages on push to `main`.

**Tech Stack:** Vanilla HTML/CSS/JS (no build step, no framework), Pyodide 0.27.x, GitHub Actions for Pages deploy.

**Spec:** [`docs/superpowers/specs/2026-07-27-pyodide-demo-design.md`](../specs/2026-07-27-pyodide-demo-design.md)

---

## File structure

```
docs/demo/
  index.html        Page shell: safety banner, hero, input panel, results panel, loader overlay, footer
  app.js            Pyodide boot, classify() wiring, render logic, masking
  styles.css        Brutalist neon-green (BLACK #000 / WHITE #FFF / NEON GREEN #00FF00)
  examples.json     Six public test-vector presets
.github/workflows/
  pages.yml         Deploy docs/demo → GitHub Pages on push to main
```

No tests directory — verification is manual browser smoke per spec.

---

### Task 1: Examples data

**Files:**
- Create: `docs/demo/examples.json`

- [ ] **Step 1: Create the examples file**

```json
[
  {
    "label": "BTC address (bech32)",
    "value": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
    "note": "Well-known P2WPKH example from BIP-173 / Bitcoin Wiki."
  },
  {
    "label": "ETH address (EIP-55 checksum)",
    "value": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "note": "vitalik.eth public donation address."
  },
  {
    "label": "Solana pubkey (base58 ed25519)",
    "value": "7xLk17EQQ5KLDLDe44wCmupJKJjTGd8hs3eSVVhCx932",
    "note": "Solana docs example pubkey."
  },
  {
    "label": "Cosmos ATOM address (20-chain HRP swap)",
    "value": "cosmos1tj20rwhd7n4yq6u27mkm9aeyaqmuv8ynvnp7g4",
    "note": "Cosmos Hub docs example. Watch the 20 cross-chain alternates."
  },
  {
    "label": "Corrupted BTC address (OCR + whitespace)",
    "value": "  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa  ",
    "note": "Bitcoin Genesis Block address with leading/trailing whitespace. Enable 'Show repair trace' to see strip-ws fire."
  },
  {
    "label": "BIP-39 mnemonic (12 words, test vector 1)",
    "value": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
    "note": "Standard BIP-39 spec test vector. Masked by default — unmasking requires confirmation."
  }
]
```

- [ ] **Step 2: Verify JSON parses**

Run: `py -c "import json; json.load(open('docs/demo/examples.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add docs/demo/examples.json
git commit -m "docs(demo): add six public test-vector examples for Pyodide demo"
```

---

### Task 2: Page shell (HTML)

**Files:**
- Create: `docs/demo/index.html`

- [ ] **Step 1: Write the HTML shell**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>crypto-key-classifier — try it in your browser</title>
  <meta name="description" content="Classify any crypto-key string client-side. BTC / ETH / SOL / Cosmos + ~50 chains. No server, no network calls.">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="loader" class="loader">
    <div class="loader__spinner"></div>
    <div class="loader__text">Booting Python…</div>
    <div class="loader__hint">First load pulls ~10MB of Pyodide + deps.</div>
  </div>

  <header class="masthead">
    <div class="masthead__wordmark">— JN</div>
    <nav class="masthead__nav">
      <a href="https://github.com/JordanNewell/crypto-key-classifier">src</a>
      <a href="https://pypi.org/project/crypto-key-classifier/">pypi</a>
    </nav>
  </header>

  <main class="page">
    <section class="hero">
      <h1 class="hero__title">crypto-key-classifier</h1>
      <p class="hero__lede">
        Paste a key. Get the chain, type, checksum, and cross-chain alternates —
        all in your browser. <strong>No server. No telemetry. The key never leaves this page.</strong>
      </p>
    </section>

    <section class="safety" aria-label="Safety notice">
      <span class="safety__icon">[LOCK]</span>
      <span class="safety__text">
        Your input never leaves your browser. Pyodide runs entirely client-side.
        No telemetry, no server, no key material transmitted.
      </span>
    </section>

    <section class="input-panel">
      <label for="key-input" class="input-panel__label">Key string</label>
      <textarea id="key-input" class="input-panel__textarea"
        rows="6" placeholder="bc1q… / 0x… / cosmos1… / 12-word mnemonic / corrupted paste"
        autocomplete="off" autocorrect="off" autocapitalize="off"
        spellcheck="false"></textarea>

      <div class="input-panel__row">
        <label class="input-panel__toggle">
          <input type="checkbox" id="explain-toggle">
          <span>Show repair trace</span>
        </label>

        <label class="input-panel__example">
          Load example:
          <select id="example-select">
            <option value="">— pick one —</option>
          </select>
        </label>

        <button id="classify-btn" class="btn btn--primary" disabled>Classify</button>
        <button id="clear-btn"  class="btn btn--ghost">Clear</button>
      </div>

      <p id="example-note" class="input-panel__note" hidden></p>
    </section>

    <section id="results" class="results" aria-live="polite"></section>
  </main>

  <footer class="footer">
    <p>
      Powered by <a href="https://pyodide.org">Pyodide</a> +
      <a href="https://github.com/JordanNewell/crypto-key-classifier">crypto-key-classifier</a> v0.6.1.
      MIT licensed.
    </p>
  </footer>

  <script src="https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js"></script>
  <script src="app.js" defer></script>
</body>
</html>
```

- [ ] **Step 2: Open in browser to confirm shell renders**

Open `file:///E:/dev/projects/crypto-key-classifier/docs/demo/index.html` in a browser.

Expected: page renders with hero text, textarea (disabled-feeling because Classify button is disabled), safety banner, and a persistent loader overlay covering the page (because Pyodide hasn't loaded — that's fine for this task). Footer present. No 404s in DevTools Network tab for `styles.css` or `app.js` (they'll be empty files but should not 404).

- [ ] **Step 3: Commit**

```bash
git add docs/demo/index.html
git commit -m "docs(demo): add HTML shell for Pyodide demo"
```

---

### Task 3: Brutalist styles

**Files:**
- Create: `docs/demo/styles.css`

- [ ] **Step 1: Write the stylesheet**

```css
:root {
  --bg: #000;
  --fg: #fff;
  --accent: #00ff00;
  --muted: #888;
  --danger: #ff3b3b;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: ui-monospace, "SF Mono", "Cascadia Mono", "JetBrains Mono", "Consolas", monospace;
  font-size: 15px;
  line-height: 1.5;
  min-height: 100vh;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ===== Loader ===== */
.loader {
  position: fixed; inset: 0;
  background: var(--bg);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 12px;
  z-index: 100;
  transition: opacity 200ms ease;
}
.loader--hidden { opacity: 0; pointer-events: none; }
.loader__spinner {
  width: 24px; height: 24px;
  border: 2px solid var(--accent);
  border-top-color: transparent;
  animation: spin 800ms linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loader__text   { font-size: 16px; color: var(--accent); }
.loader__hint   { font-size: 12px; color: var(--muted); }

/* ===== Masthead ===== */
.masthead {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--accent);
}
.masthead__wordmark { color: var(--accent); letter-spacing: 2px; }
.masthead__nav a { margin-left: 16px; }

/* ===== Page ===== */
.page { max-width: 880px; margin: 0 auto; padding: 32px 24px 80px; }

/* ===== Hero ===== */
.hero { margin-bottom: 24px; }
.hero__title {
  font-size: 32px; letter-spacing: -1px; margin: 0 0 8px;
  color: var(--accent);
}
.hero__lede { color: var(--fg); margin: 0; }
.hero__lede strong { color: var(--accent); }

/* ===== Safety banner ===== */
.safety {
  border: 1px solid var(--accent);
  padding: 12px 16px;
  margin-bottom: 32px;
  font-size: 13px;
  display: flex; gap: 12px; align-items: flex-start;
}
.safety__icon { color: var(--accent); font-weight: bold; }

/* ===== Input panel ===== */
.input-panel { margin-bottom: 32px; }
.input-panel__label {
  display: block; font-size: 12px; color: var(--muted);
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
}
.input-panel__textarea {
  width: 100%; resize: vertical;
  background: var(--bg); color: var(--fg);
  border: 1px solid var(--accent);
  padding: 12px;
  font: inherit;
  word-break: break-all;
}
.input-panel__textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.input-panel__row {
  display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
  margin-top: 16px;
}
.input-panel__toggle { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.input-panel__example { display: flex; align-items: center; gap: 8px; }
.input-panel__example select {
  background: var(--bg); color: var(--fg);
  border: 1px solid var(--accent);
  padding: 4px 8px; font: inherit;
}
.input-panel__note {
  margin-top: 12px; font-size: 12px; color: var(--muted);
  font-style: italic;
}

/* ===== Buttons ===== */
.btn {
  font: inherit; padding: 6px 16px;
  border: 1px solid var(--accent);
  background: transparent; color: var(--accent);
  cursor: pointer;
  text-transform: uppercase; letter-spacing: 1px;
}
.btn--primary { background: var(--accent); color: var(--bg); font-weight: bold; }
.btn--ghost   { color: var(--muted); border-color: var(--muted); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ===== Results ===== */
.results:empty::before {
  content: "Results will appear here.";
  display: block; padding: 24px; text-align: center;
  color: var(--muted); font-style: italic;
  border: 1px dashed var(--muted);
}
.results__empty, .results__error {
  padding: 16px; border: 1px solid var(--muted);
  color: var(--muted); margin: 0;
}
.results__error { border-color: var(--danger); color: var(--danger); }

.match-card {
  border: 1px solid var(--accent);
  padding: 16px; margin-bottom: 16px;
}
.match-card__head {
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  margin-bottom: 12px;
}
.match-card__chain {
  font-weight: bold; color: var(--bg);
  background: var(--accent);
  padding: 2px 8px;
}
.match-card__type  { color: var(--accent); }
.match-card__conf  { margin-left: auto; font-size: 12px; color: var(--muted); }
.match-card__bar {
  height: 4px; background: var(--muted); margin-top: 4px;
}
.match-card__bar > span {
  display: block; height: 100%; background: var(--accent);
}
.match-card__row {
  display: grid; grid-template-columns: 120px 1fr;
  gap: 8px; margin-top: 8px; font-size: 13px;
}
.match-card__row > dt { color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-size: 11px; }
.match-card__row > dd { margin: 0; word-break: break-all; }
.match-card__key { font-family: inherit; }
.match-card__unmask {
  background: transparent; border: 1px solid var(--accent);
  color: var(--accent); font: inherit; font-size: 11px;
  padding: 1px 6px; margin-left: 8px; cursor: pointer;
}
.match-card__section {
  margin-top: 12px; border-top: 1px dashed var(--muted); padding-top: 8px;
}
.match-card__section-title {
  font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px;
  cursor: pointer; margin: 0 0 8px;
}
.match-card__section-title::before { content: "[+] "; color: var(--accent); }
.match-card__section--open .match-card__section-title::before { content: "[-] "; }
.match-card__section-body { font-size: 13px; }
.match-card__section:not(.match-card__section--open) .match-card__section-body { display: none; }
.match-card__alt {
  display: grid; grid-template-columns: 80px 1fr; gap: 8px;
  padding: 2px 0;
}
.match-card__alt > code {
  color: var(--accent); font-family: inherit;
}
.match-card__trace { font-size: 12px; color: var(--muted); margin: 0; white-space: pre-wrap; }

/* ===== Footer ===== */
.footer {
  border-top: 1px solid var(--accent);
  padding: 24px; text-align: center; font-size: 12px; color: var(--muted);
}
.footer a { color: var(--accent); }
```

- [ ] **Step 2: Reload browser, confirm visual**

Reload the page from Task 2.

Expected: BLACK background, WHITE body text, NEON GREEN accents. Hero title in green. Safety banner with green border. Textarea with green border. Classify button green-on-black, Clear button ghost. Results area shows italic placeholder. Loader overlay still covering.

- [ ] **Step 3: Commit**

```bash
git add docs/demo/styles.css
git commit -m "docs(demo): brutalist neon-green brand styles"
```

---

### Task 4: Pyodide boot

**Files:**
- Create: `docs/demo/app.js`

- [ ] **Step 1: Write app.js with boot logic only (no rendering yet)**

```js
// crypto-key-classifier demo — Pyodide boot + classify wiring.
// Pinned versions:
//   pyodide: 0.27.2
//   crypto-key-classifier: 0.6.1

const CKC_VERSION = "0.6.1";

const els = {
  loader:        document.getElementById("loader"),
  input:         document.getElementById("key-input"),
  explainToggle: document.getElementById("explain-toggle"),
  exampleSelect: document.getElementById("example-select"),
  exampleNote:   document.getElementById("example-note"),
  classifyBtn:   document.getElementById("classify-btn"),
  clearBtn:      document.getElementById("clear-btn"),
  results:       document.getElementById("results"),
};

let classifyFn = null;
let examplesCache = null;

function setLoader(message, hint) {
  els.loader.querySelector(".loader__text").textContent = message;
  if (hint !== undefined) {
    els.loader.querySelector(".loader__hint").textContent = hint;
  }
}

function hideLoader() {
  els.loader.classList.add("loader--hidden");
}

function showError(message) {
  els.results.innerHTML = "";
  const p = document.createElement("p");
  p.className = "results__error";
  p.textContent = message;
  els.results.appendChild(p);
}

async function bootPyodide() {
  setLoader("Loading Pyodide runtime…");
  // loadPyodide is provided by the pyodide.js script tag.
  const pyodide = await loadPyodide();

  setLoader("Loading micropip…");
  await pyodide.loadPackage("micropip");

  setLoader(
    `Installing crypto-key-classifier==${CKC_VERSION}…`,
    "Pulling pycryptodome + base58 + ckc."
  );
  await pyodide.runPythonAsync(
    `import micropip\nawait micropip.install("crypto-key-classifier==${CKC_VERSION}")`
  );

  setLoader("Wiring classify()…");
  const pipeline = pyodide.pyimport("ckc.pipeline");
  classifyFn = pipeline.classify;
}

async function loadExamples() {
  const res = await fetch("examples.json");
  if (!res.ok) {
    console.warn("examples.json failed to load", res.status);
    return [];
  }
  examplesCache = await res.json();
  for (const ex of examplesCache) {
    const opt = document.createElement("option");
    opt.value = ex.value;
    opt.textContent = ex.label;
    els.exampleSelect.appendChild(opt);
  }
  return examplesCache;
}

function init() {
  els.classifyBtn.disabled = true;
  els.clearBtn.addEventListener("click", () => {
    els.input.value = "";
    els.results.innerHTML = "";
    els.exampleSelect.value = "";
    els.exampleNote.hidden = true;
    els.input.focus();
  });
  els.exampleSelect.addEventListener("change", (e) => {
    const value = e.target.value;
    if (!value) {
      els.exampleNote.hidden = true;
      return;
    }
    els.input.value = value;
    const match = (examplesCache || []).find((x) => x.value === value);
    if (match) {
      els.exampleNote.textContent = match.note;
      els.exampleNote.hidden = false;
    }
  });
}

init();

(async () => {
  try {
    await loadExamples();
    await bootPyodide();
    els.classifyBtn.disabled = false;
    hideLoader();
    els.input.focus();
  } catch (err) {
    console.error("boot failed", err);
    setLoader("Boot failed.");
    showError(
      "Browser Python failed to load. Refresh? Details in DevTools console. " +
      String(err && err.message ? err.message : err)
    );
    hideLoader();
  }
})();
```

- [ ] **Step 2: Syntax check**

Run: `node --check docs/demo/app.js`
Expected: no output, exit 0.

- [ ] **Step 3: Open in browser, watch DevTools console**

Open page. Watch DevTools → Network and Console.

Expected sequence:
1. Loader appears, text cycles: "Loading Pyodide runtime…" → "Loading micropip…" → "Installing crypto-key-classifier==0.6.1…" → "Wiring classify()…"
2. Total boot 3–10 seconds.
3. Loader fades out, Classify button becomes enabled.
4. Console: no errors.

If `micropip.install` fails with a wheel-fetch CORS error or 404, stop and report — spec's risks section anticipated this.

- [ ] **Step 4: Commit**

```bash
git add docs/demo/app.js
git commit -m "docs(demo): Pyodide boot + ckc.classify wiring"
```

---

### Task 5: Render classify result

**Files:**
- Modify: `docs/demo/app.js` (add rendering + submit handler)

- [ ] **Step 1: Append render functions and submit handler to app.js**

Append to the bottom of `docs/demo/app.js`:

```js
function classifyAndRender() {
  const input = els.input.value.trim();
  els.results.innerHTML = "";
  if (!input) return;

  let matches;
  try {
    // classify(raw) returns a Python list[Match]; .toJs() converts to JS Array.
    matches = classifyFn(input).toJs();
  } catch (err) {
    showError("Classifier threw: " + String(err && err.message ? err.message : err));
    return;
  }

  if (!matches || matches.length === 0) {
    const p = document.createElement("p");
    p.className = "results__empty";
    if (els.explainToggle.checked) {
      p.textContent = "No match even after aggressive recovery. Input may be truncated or wrong charset.";
    } else {
      p.textContent = "No classifier matched this input. Try enabling 'Show repair trace'.";
    }
    els.results.appendChild(p);
    return;
  }

  for (const m of matches) {
    els.results.appendChild(renderMatch(m));
  }
}

function renderMatch(m) {
  // m is a Python Match dataclass; access fields via . attribute (Pyodide lets us).
  const card = document.createElement("article");
  card.className = "match-card";

  const head = document.createElement("div");
  head.className = "match-card__head";
  head.innerHTML = `
    <span class="match-card__chain"></span>
    <span class="match-card__type"></span>
    <span class="match-card__conf"></span>
  `;
  head.querySelector(".match-card__chain").textContent = m.chain;
  head.querySelector(".match-card__type").textContent  = m.format + " · " + m.key_type;
  head.querySelector(".match-card__conf").textContent  = "confidence " + m.confidence + "%";
  card.appendChild(head);

  const bar = document.createElement("div");
  bar.className = "match-card__bar";
  const fill = document.createElement("span");
  fill.style.width = m.confidence + "%";
  bar.appendChild(fill);
  card.appendChild(bar);

  const dl = document.createElement("dl");
  dl.className = "match-card__row";
  const rows = [
    ["checksum", m.checksum_status],
    ["network",  m.network || "—"],
    ["notes",    (m.notes && m.notes.toJs ? m.notes.toJs() : m.notes || []).join("; ") || "—"],
    ["wallets",  (m.wallet_compatibility && m.wallet_compatibility.toJs ? m.wallet_compatibility.toJs() : m.wallet_compatibility || []).join(", ") || "—"],
  ];
  for (const [k, v] of rows) {
    const dt = document.createElement("dt"); dt.textContent = k;
    const dd = document.createElement("dd"); dd.textContent = v;
    dl.appendChild(dt); dl.appendChild(dd);
  }
  card.appendChild(dl);

  // Masked key
  const keyRow = document.createElement("p");
  keyRow.className = "match-card__row";
  keyRow.style.gridTemplateColumns = "120px 1fr";
  const keyLabel = document.createElement("span");
  keyLabel.textContent = "input";
  keyLabel.style.color = "var(--muted)";
  keyLabel.style.fontSize = "11px";
  keyLabel.style.textTransform = "uppercase";
  keyLabel.style.letterSpacing = "1px";
  keyLabel.style.alignSelf = "start";
  const keySpan = document.createElement("span");
  keySpan.className = "match-card__key";
  keySpan.dataset.sensitive = isSensitive(m) ? "1" : "0";
  renderMaskedKey(keySpan, els.input.value);
  keyRow.appendChild(keyLabel); keyRow.appendChild(keySpan);
  card.appendChild(keyRow);

  // Cross-chain alternates (collapsible)
  const alternates = listToJs(m.cross_chain_alternates);
  if (alternates && alternates.length) {
    card.appendChild(renderCollapsible(
      "Cross-chain alternates (" + alternates.length + ")",
      () => {
        const body = document.createElement("div");
        for (const pair of alternates) {
          const [chainCode, altKey] = Array.isArray(pair) ? pair : [pair.get(0), pair.get(1)];
          const row = document.createElement("div");
          row.className = "match-card__alt";
          const code = document.createElement("code");
          code.textContent = chainCode;
          const val = document.createElement("span");
          val.style.wordBreak = "break-all";
          val.textContent = altKey;
          row.appendChild(code); row.appendChild(val);
          body.appendChild(row);
        }
        return body;
      }
    ));
  }

  // Repair trace (collapsible, only if toggle on AND repairs exist)
  const repairs = listToJs(m.repairs_applied);
  if (els.explainToggle.checked && repairs && repairs.length) {
    card.appendChild(renderCollapsible(
      "Repair trace (" + repairs.length + ")",
      () => {
        const pre = document.createElement("pre");
        pre.className = "match-card__trace";
        pre.textContent = repairs.map((r, i) => (i + 1) + ". " + r).join("\n");
        return pre;
      }
    ));
  }

  return card;
}

function isSensitive(m) {
  return m.key_type === "private-key" || m.key_type === "mnemonic";
}

function renderMaskedKey(span, raw) {
  const isSensitive = span.dataset.sensitive === "1";
  if (!isSensitive) {
    span.textContent = raw;
    return;
  }
  span.dataset.raw = raw;
  span.dataset.unmasked = "0";
  span.textContent = maskValue(raw);
  const btn = document.createElement("button");
  btn.className = "match-card__unmask";
  btn.textContent = "unmask";
  btn.addEventListener("click", () => {
    if (span.dataset.unmasked === "1") {
      span.dataset.unmasked = "0";
      span.textContent = maskValue(raw);
      const b2 = document.createElement("button");
      b2.className = "match-card__unmask";
      b2.textContent = "unmask";
      b2.addEventListener("click", clickUnmask);
      span.appendChild(b2);
      return;
    }
    clickUnmask();
  });
  function clickUnmask() {
    const ok = window.confirm(
      "This will display a sensitive key in plaintext.\n\n" +
      "Make sure no one is shoulder-surfing and you don't have a screen recorder running.\n\n" +
      "Continue?"
    );
    if (!ok) return;
    span.dataset.unmasked = "1";
    span.textContent = raw;
    const b2 = document.createElement("button");
    b2.className = "match-card__unmask";
    b2.textContent = "mask";
    b2.addEventListener("click", () => {
      span.dataset.unmasked = "0";
      span.textContent = maskValue(raw);
      const b3 = document.createElement("button");
      b3.className = "match-card__unmask";
      b3.textContent = "unmask";
      b3.addEventListener("click", clickUnmask);
      span.appendChild(b3);
    });
    span.appendChild(b2);
  }
  span.appendChild(btn);
}

function maskValue(raw) {
  if (!raw) return "";
  if (raw.length <= 12) {
    return raw.slice(0, 2) + "…" + raw.slice(-2) + " (" + (raw.length - 4) + " chars masked)";
  }
  return raw.slice(0, 4) + "…" + raw.slice(-4) + " (" + (raw.length - 8) + " chars masked)";
}

function renderCollapsible(title, bodyFactory) {
  const sec = document.createElement("div");
  sec.className = "match-card__section";
  const t = document.createElement("p");
  t.className = "match-card__section-title";
  t.textContent = title;
  sec.appendChild(t);
  const body = document.createElement("div");
  body.className = "match-card__section-body";
  body.appendChild(bodyFactory());
  sec.appendChild(body);
  t.addEventListener("click", () => sec.classList.toggle("match-card__section--open"));
  // Default open so the differentiator (cross-chain, repair trace) is visible without an extra click.
  sec.classList.add("match-card__section--open");
  return sec;
}

function listToJs(v) {
  if (!v) return [];
  if (typeof v.toJs === "function") return v.toJs();
  if (Array.isArray(v)) return v;
  return [];
}

els.classifyBtn.addEventListener("click", classifyAndRender);
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    classifyAndRender();
  }
});
```

- [ ] **Step 2: Syntax check**

Run: `node --check docs/demo/app.js`
Expected: no output, exit 0.

- [ ] **Step 3: Browser smoke — all six examples**

Reload page, wait for boot.

For each of the six examples in the dropdown:
1. Select it from dropdown.
2. Click Classify.
3. Verify a card renders with the correct chain in the green badge.

Specifically verify:
- BTC example → badge says "BTC", type includes "address", checksum "valid", confidence visible.
- ETH example → badge "ETH", checksum "valid" (EIP-55).
- SOL example → badge "SOL".
- ATOM example → badge "ATOM" (or "COSMOS"), and cross-chain alternates section shows 20 entries when expanded.
- Corrupted BTC → badge "BTC", repair trace section appears when "Show repair trace" checkbox is on; does NOT appear when checkbox is off.
- Mnemonic → badge "MNEMONIC" (or similar), input shown masked with "unmask" button, clicking unmask shows confirm dialog.

- [ ] **Step 4: Browser smoke — no-match path**

Type `hello world this is not a key` into textarea, click Classify.
Expected: "No classifier matched this input. Try enabling 'Show repair trace'."

Enable repair trace toggle, click Classify again.
Expected: "No match even after aggressive recovery. Input may be truncated or wrong charset."

- [ ] **Step 5: Commit**

```bash
git add docs/demo/app.js
git commit -m "docs(demo): render classify results — cards, cross-chain, repair trace"
```

---

### Task 6: GitHub Pages deploy workflow

**Files:**
- Create: `.github/workflows/pages.yml`

- [ ] **Step 1: Confirm `.github/workflows/` exists**

Run: `ls E:/dev/projects/crypto-key-classifier/.github/workflows/`
Expected: shows existing `ci.yml` (per git log `b4dfd42 ci: add GitHub Actions workflow`).

- [ ] **Step 2: Write the workflow**

```yaml
name: Deploy demo to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - 'docs/demo/**'
      - '.github/workflows/pages.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

# Allow only one concurrent deployment.
concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/demo
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Validate YAML**

Run:
```bash
py -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml'))"
```
Expected: no output, exit 0.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/pages.yml
git commit -m "ci: deploy docs/demo to GitHub Pages on push to main"
```

---

### Task 7: Wire up GitHub Pages source setting + push

**This task requires the user (push + repo settings UI). The implementer should stop and hand back to user after Step 1.**

- [ ] **Step 1: Verify nothing else to commit**

Run: `cd E:/dev/projects/crypto-key-classifier && git status --short && git log --oneline -6`
Expected: clean tree, last 5 commits are: spec, examples, html, css, app, app-render, workflow.

- [ ] **Step 2: Hand off to user — repo Settings → Pages → Source: GitHub Actions**

User action only. Implementer cannot do this.

- [ ] **Step 3: Hand off to user — push to origin**

User action: `git push origin main`

- [ ] **Step 4: Verify deployment**

User action: watch https://github.com/JordanNewell/crypto-key-classifier/actions for the `Deploy demo to GitHub Pages` run. Once green, open https://jordannewell.github.io/crypto-key-classifier/ and repeat the Task 5 browser smoke against the deployed URL.

---

### Task 8: Final verification

Invoke `superpowers:verification-before-completion` skill and run its checklist. Specifically confirm:

- [ ] Deployed URL loads.
- [ ] Boot completes within ~10s.
- [ ] All six examples classify correctly.
- [ ] ATOM example shows 20 cross-chain alternates.
- [ ] Corrupted BTC shows repair trace with toggle on, hides with toggle off.
- [ ] Mnemonic masks by default, unmask requires confirm dialog.
- [ ] No-match path shows both messages correctly.
- [ ] Safety banner is visible and accurate.
- [ ] No errors in DevTools console after a clean boot.

If any fail, do NOT declare done. File as a follow-up task or fix inline.

---

## Self-review (run after writing this plan)

**Spec coverage:**
- ✅ Goal: single-page demo at the URL — Tasks 2-7
- ✅ Pyodide + micropip approach — Task 4
- ✅ Three-file layout — Tasks 2, 3, 4
- ✅ examples.json with 6 public vectors — Task 1
- ✅ Brutalist neon-green brand — Task 3
- ✅ Input panel + result cards — Tasks 2, 5
- ✅ Repair trace toggle — Task 5
- ✅ Cross-chain alternates — Task 5
- ✅ Masking for sensitive types — Task 5 (renderMaskedKey + isSensitive)
- ✅ Safety banner — Task 2 (HTML) + Task 3 (CSS)
- ✅ Error handling (load fail, empty, no-match, exception, unmask confirm) — Tasks 4, 5
- ✅ GitHub Actions deploy — Task 6
- ✅ Manual smoke — Task 5 (during dev) + Task 8 (final)
- ✅ Version pin CKC_VERSION="0.6.1" — Task 4
- ✅ No real mainnet keys — Task 1 (all examples public/well-known)

**Placeholder scan:** none.

**Type consistency:** `classifyFn`, `els`, `CKC_VERSION`, `examplesCache` — referenced consistently. Field names match Python `Match` dataclass (`chain`, `format`, `key_type`, `confidence`, `checksum_status`, `network`, `cross_chain_alternates`, `wallet_compatibility`, `repairs_applied`, `notes`).

**Known small risk:** `cross_chain_alternates` is `list[tuple[str, str]]` on the Python side. Pyodide's `.toJs()` on a list of tuples may return either JS Array-of-Arrays or Array-of-Maps. The render code handles both via the `Array.isArray(pair) ? pair : [pair.get(0), pair.get(1)]` branch. If Pyodide returns neither shape, the render will throw and we'll need to add a `pair instanceof Map` branch. Acceptable to discover at Task 5 smoke.
