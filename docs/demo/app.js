// crypto-key-classifier demo — Pyodide boot + classify wiring.
// Pinned versions:
//   pyodide: 0.27.2
//   crypto-key-classifier: 0.6.1

const CKC_VERSION = "0.6.1";

const els = {
  loader:        document.getElementById("loader"),
  input:         document.getElementById("key-input"),
  explainToggle: document.getElementById("explain-toggle"),
  unmaskToggle:  document.getElementById("unmask-toggle"),
  exampleSelect: document.getElementById("example-select"),
  exampleNote:   document.getElementById("example-note"),
  classifyBtn:   document.getElementById("classify-btn"),
  clearBtn:      document.getElementById("clear-btn"),
  shareBtn:      document.getElementById("share-btn"),
  downloadBtn:   document.getElementById("download-btn"),
  historyBtn:    document.getElementById("history-btn"),
  historyPopover:document.getElementById("history-popover"),
  bulkIndicator: document.getElementById("bulk-indicator"),
  unmaskBanner:  document.getElementById("unmask-banner"),
  results:       document.getElementById("results"),
  freshness:     document.getElementById("freshness"),
  starCount:     document.getElementById("star-count"),
  shortcutsOverlay: document.getElementById("shortcuts-overlay"),
};

let classifyFn = null;
let examplesCache = null;
// Most-recent classify output, used by Download JSON. Reset on every classify().
let lastResults = null;
const HISTORY_KEY = "ckc-history";
const HISTORY_MAX = 5;

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

function slugify(label) {
  return String(label)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function findOptionBySlug(slug) {
  if (!slug) return null;
  for (const opt of els.exampleSelect.options) {
    if (opt.dataset.slug === slug) return opt;
  }
  return null;
}

// ===== Share URL =====
// Encoding scheme (URL-safe, no padding):
//   #example=<slug>           — example-only share (preserved for backward compat)
//   #k=<b64url>               — arbitrary input + toggle state
// The b64url payload is a tiny JSON: {"k":input,"e":explain,"u":unmask}
// Keys kept single-char to keep URLs short. Input is the user's paste, so
// we encode (not encrypt) — the hash is plaintext to anyone who reads the URL.
function b64urlEncode(str) {
  // UTF-8 safe: TextEncoder → bytes → base64 → url-safe.
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  const b64 = btoa(bin);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function b64urlDecode(str) {
  const pad = str.length % 4 === 0 ? "" : "=".repeat(4 - (str.length % 4));
  const b64 = (str + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

function buildSharePayload() {
  const payload = {
    k: els.input.value || "",
    e: !!(els.explainToggle && els.explainToggle.checked),
    u: !!(els.unmaskToggle && els.unmaskToggle.checked),
  };
  return JSON.stringify(payload);
}

function buildShareHash() {
  // Empty input → no shareable state. Fall back to clearing the hash.
  if (!els.input.value || !els.input.value.trim()) return "";
  return "#k=" + b64urlEncode(buildSharePayload());
}

function readShareFromHash() {
  const hash = window.location.hash || "";
  const exMatch = hash.match(/^#example=(.+)$/);
  if (exMatch) {
    const slug = decodeURIComponent(exMatch[1]);
    const opt = findOptionBySlug(slug);
    if (!opt) return null;
    return {
      input: opt.value,
      explain: false,
      unmask: false,
      exampleSlug: slug,
      exampleValue: opt.value,
    };
  }
  const kMatch = hash.match(/^#k=(.+)$/);
  if (!kMatch) return null;
  try {
    const payload = JSON.parse(b64urlDecode(kMatch[1]));
    if (typeof payload !== "object" || payload === null) return null;
    return {
      input: typeof payload.k === "string" ? payload.k : "",
      explain: !!payload.e,
      unmask: !!payload.u,
    };
  } catch {
    return null;
  }
}

function applyShareState(state) {
  if (!state) return false;
  if (typeof state.explain === "boolean" && els.explainToggle) {
    els.explainToggle.checked = state.explain;
  }
  // Unmask requires the 3-confirmation flow on manual toggle. A share URL with
  // unmask=true is opt-in by the sender, but we still force it off on load and
  // let the user re-arm it — auto-revealing keys via a clicked link is a footgun.
  if (els.unmaskToggle) els.unmaskToggle.checked = false;
  showUnmaskBanner(false);

  if (state.exampleValue) {
    els.exampleSelect.value = state.exampleValue;
    const ex = (examplesCache || []).find((x) => x.value === state.exampleValue);
    if (ex && ex.note) {
      els.exampleNote.textContent = ex.note;
      els.exampleNote.hidden = false;
    }
  } else {
    els.exampleSelect.value = "";
    els.exampleNote.hidden = true;
  }
  els.input.value = state.input || "";
  updateBulkIndicator();
  return true;
}

function syncHashFromState() {
  const hash = buildShareHash();
  const current = window.location.hash || "";
  if (current === hash) return;
  if (hash) {
    history.replaceState(null, "", hash);
  } else if (current) {
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }
  // Share button is live whenever there is shareable input.
  const hasInput = !!(els.input.value && els.input.value.trim());
  if (els.shareBtn) els.shareBtn.disabled = !hasInput;
}

function applyHashExample() {
  // Deprecated — superseded by readShareFromHash() + applyShareState() in the
  // boot flow. Kept as a no-op stub so any external callers don't throw.
  return false;
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
    opt.dataset.slug = slugify(ex.label);
    els.exampleSelect.appendChild(opt);
  }
  // Share-state application happens in the boot flow after Pyodide is ready,
  // so auto-classify doesn't fire before classifyFn is wired.
  return examplesCache;
}

function compareVersions(a, b) {
  // Loose dotted-numeric compare; non-numeric suffixes (-rc1, +build) are ignored.
  const pa = String(a).split("."); const pb = String(b).split(".");
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const ai = parseInt(pa[i] || "0", 10) || 0;
    const bi = parseInt(pb[i] || "0", 10) || 0;
    if (ai !== bi) return ai < bi ? -1 : 1;
  }
  return 0;
}

async function refreshFreshness() {
  // PyPI JSON supports CORS. Silent-fail: stale info is worse than no info.
  try {
    const res = await fetch("https://pypi.org/pypi/crypto-key-classifier/json");
    if (!res.ok) return;
    const data = await res.json();
    const latest = data && data.info && data.info.version;
    if (!latest) return;
    renderFreshness(latest);
  } catch {
    /* network/CORS/down — just leave the badge hidden */
  }
}

function renderFreshness(latest) {
  const el = els.freshness;
  if (!el) return;
  const cmp = compareVersions(CKC_VERSION, latest);
  if (cmp === 0) {
    el.textContent = "v" + CKC_VERSION + " · latest";
    el.classList.remove("freshness--stale");
    el.removeAttribute("href");
  } else {
    el.classList.add("freshness--stale");
    el.textContent = "";
    el.appendChild(document.createTextNode("v" + CKC_VERSION + " → "));
    const link = document.createElement("a");
    link.href = "https://pypi.org/project/crypto-key-classifier/";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = latest;
    el.appendChild(link);
    el.appendChild(document.createTextNode(" available"));
  }
  el.hidden = false;
}

async function refreshStarCount() {
  // Unauthenticated GitHub REST is rate-limited per IP; cache in sessionStorage so
  // subsequent loads (common with PWA/SW offline retries) don't burn the budget.
  const KEY = "ckc-demo:stars";
  try {
    const cached = sessionStorage.getItem(KEY);
    if (cached) { renderStarCount(cached); return; }
    const res = await fetch("https://api.github.com/repos/JordanNewell/crypto-key-classifier");
    if (!res.ok) return;
    const data = await res.json();
    const count = data && typeof data.stargazers_count === "number"
      ? String(data.stargazers_count)
      : null;
    if (!count) return;
    sessionStorage.setItem(KEY, count);
    renderStarCount(count);
  } catch {
    /* rate-limited or offline — just hide count */
  }
}

function renderStarCount(count) {
  const el = els.starCount;
  if (!el) return;
  el.textContent = " " + count;
  el.hidden = false;
}

function splitBulkKeys(input) {
  // Split on newlines, drop empties. Single-line input returns a 1-element array,
  // which keeps the non-bulk render path as a strict subset of the bulk path.
  // DO NOT trim the line itself — classify()'s preprocessor handles whitespace,
  // and trimming here would mask the strip-ws repair that the demo exists to show.
  return input
    .split(/\r\n|\r|\n/)
    .filter((line) => line.trim().length > 0);
}

function updateBulkIndicator() {
  const keys = splitBulkKeys(els.input.value);
  if (keys.length >= 2) {
    els.bulkIndicator.textContent = "Bulk mode: " + keys.length + " keys";
    els.bulkIndicator.hidden = false;
  } else {
    els.bulkIndicator.hidden = true;
  }
}

function init() {
  els.classifyBtn.disabled = true;
  els.clearBtn.addEventListener("click", () => {
    els.input.value = "";
    els.results.innerHTML = "";
    els.exampleSelect.value = "";
    els.exampleNote.hidden = true;
    lastResults = null;
    updateDownloadBtn();
    updateBulkIndicator();
    syncHashFromState();
    els.input.focus();
  });
  els.exampleSelect.addEventListener("change", (e) => {
    const value = e.target.value;
    const selected = e.target.options[e.target.selectedIndex];
    if (!value) {
      els.exampleNote.hidden = true;
      els.input.value = "";
      updateBulkIndicator();
      syncHashFromState();
      return;
    }
    els.input.value = value;
    const match = (examplesCache || []).find((x) => x.value === value);
    if (match) {
      els.exampleNote.textContent = match.note;
      els.exampleNote.hidden = false;
    }
    updateBulkIndicator();
    syncHashFromState();
  });
  els.input.addEventListener("input", () => {
    updateBulkIndicator();
    // Live-update the share hash so the URL is always deep-linkable to current state.
    // We do NOT auto-clear the example dropdown here — that would lose the note.
    syncHashFromState();
  });
  els.explainToggle.addEventListener("change", syncHashFromState);
  initUnmaskToggle();
  initShareButton();
  initDownloadButton();
  initHistoryPopover();
  initKeyboardShortcuts();
}

init();

(async () => {
  try {
    await loadExamples();
    await bootPyodide();
    els.classifyBtn.disabled = false;
    hideLoader();
    // Apply any share state from the URL hash BEFORE focusing the input —
    // a share link should auto-populate + auto-classify on load.
    const shared = readShareFromHash();
    if (shared && shared.input) {
      applyShareState(shared);
      // Auto-classify so the share recipient sees results immediately.
      classifyAndRender();
    } else {
      els.input.focus();
    }
    // Fire-and-forget; failure is silent and doesn't block the demo.
    refreshFreshness();
    refreshStarCount();
    updateHistoryBtn();
    updateDownloadBtn();
    syncHashFromState();
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

// ===== Classify + render =====

function classifyAndRender() {
  // Don't trim — classify()'s preprocessor handles whitespace, confusables, etc.
  // Trimming here would mask the very repair features the demo exists to show off.
  const input = els.input.value;
  els.results.innerHTML = "";
  lastResults = null;
  updateDownloadBtn();
  if (!input || !input.trim()) return;

  const keys = splitBulkKeys(input);
  if (keys.length === 0) return;

  const isBulk = keys.length >= 2;
  const globalUnmask = !!(els.unmaskToggle && els.unmaskToggle.checked);

  const collected = [];
  if (isBulk) {
    for (let i = 0; i < keys.length; i++) {
      const group = renderKeyGroup(keys[i], i + 1, keys.length, globalUnmask, collected);
      els.results.appendChild(group);
    }
  } else {
    els.results.appendChild(renderKeyGroup(keys[0], 1, 1, globalUnmask, collected));
  }

  // Persist results for Download JSON.
  if (collected.length > 0) {
    lastResults = {
      generatedAt: new Date().toISOString(),
      input: keys,
      results: collected,
    };
    updateDownloadBtn();
    // History tracks the raw input(s). Multiple keys → one combined entry
    // joined by newlines so the user gets the full bulk set back on click.
    addToHistory(keys.join("\n"));
  }

  // Refresh the share hash so it reflects the just-classified state.
  syncHashFromState();
}

function renderKeyGroup(rawKey, idx, total, globalUnmask, collected) {
  // Group wrapper: holds the label + each Match card. Even single-key renders go
  // through this so the layout math stays uniform.
  const group = document.createElement("div");
  group.className = "key-group";

  const label = document.createElement("div");
  label.className = "key-group__label";
  const labelTxt = document.createElement("span");
  labelTxt.className = "key-group__label-text";
  if (total > 1) {
    labelTxt.textContent = "Key " + idx + "/" + total + ": " + truncateKey(rawKey) + "…";
  } else {
    labelTxt.textContent = "Input: " + truncateKey(rawKey) + "…";
  }
  label.appendChild(labelTxt);
  label.appendChild(makeCopyButton(() => rawKey));
  group.appendChild(label);

  let matches;
  try {
    matches = classifyFn(rawKey).toJs();
  } catch (err) {
    const p = document.createElement("p");
    p.className = "results__error";
    p.textContent = "Classifier threw: " + String(err && err.message ? err.message : err);
    group.appendChild(p);
    return group;
  }

  if (!matches || matches.length === 0) {
    const p = document.createElement("p");
    p.className = "results__empty";
    if (els.explainToggle.checked) {
      p.textContent = "No match even after aggressive recovery. Input may be truncated or wrong charset.";
    } else {
      p.textContent = "No classifier matched this input. Try enabling 'Show repair trace'.";
    }
    group.appendChild(p);
    return group;
  }

  for (const m of matches) {
    group.appendChild(renderMatch(m, rawKey, globalUnmask));
    if (collected) collected.push(serializeMatch(m, rawKey));
  }
  return group;
}

// Snapshot a Match dataclass into a plain JSON-safe object. We pull every
// attribute defensively because the Pydantic schema may grow across versions —
// unknown attrs are silently dropped rather than crashing the download.
function serializeMatch(m, rawKey) {
  const out = {
    input: rawKey,
    chain: getattr(m, "chain"),
    format: getattr(m, "format"),
    key_type: getattr(m, "key_type"),
    confidence: getattr(m, "confidence"),
    checksum_status: getattr(m, "checksum_status"),
    network: getattr(m, "network"),
    notes: listToJs(getattr(m, "notes")),
    wallet_compatibility: listToJs(getattr(m, "wallet_compatibility")),
    repairs_applied: listToJs(getattr(m, "repairs_applied")),
  };
  const alts = listToJs(getattr(m, "cross_chain_alternates"));
  out.cross_chain_alternates = alts.map((pair) => {
    if (Array.isArray(pair)) return [pair[0], pair[1]];
    if (pair && typeof pair.get === "function") return [pair.get(0), pair.get(1)];
    return [String(pair)];
  });
  return out;
}

function getattr(obj, name) {
  if (obj == null) return null;
  if (typeof obj.get === "function" && (name === 0 || typeof name === "string")) {
    try { return obj.get(name); } catch { /* fall through */ }
  }
  return obj[name];
}

function truncateKey(raw) {
  if (raw.length <= 16) return raw;
  return raw.slice(0, 16);
}

function renderMatch(m, rawKey, globalUnmask) {
  // m is a Python Match dataclass accessed via attribute.
  const card = document.createElement("article");
  card.className = "match-card";

  const head = document.createElement("div");
  head.className = "match-card__head";
  const chainBadge = document.createElement("span");
  chainBadge.className = "match-card__chain";
  chainBadge.textContent = m.chain;
  const typeSpan = document.createElement("span");
  typeSpan.className = "match-card__type";
  typeSpan.textContent = m.format + " · " + m.key_type;
  const confSpan = document.createElement("span");
  confSpan.className = "match-card__conf";
  confSpan.textContent = "confidence " + m.confidence + "%";
  head.appendChild(chainBadge);
  head.appendChild(typeSpan);
  head.appendChild(confSpan);
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

  // Input row (masked if sensitive, unless global unmask is on)
  const keyRow = document.createElement("div");
  keyRow.className = "match-card__row";
  const keyLabel = document.createElement("span");
  keyLabel.textContent = "input";
  const keySpan = document.createElement("span");
  keySpan.className = "match-card__key";
  keySpan.dataset.sensitive = isSensitive(m) ? "1" : "0";
  renderMaskedKey(keySpan, rawKey, globalUnmask);
  keyRow.appendChild(keyLabel);
  keyRow.appendChild(keySpan);
  card.appendChild(keyRow);

  // Cross-chain alternates (collapsible)
  const alternates = listToJs(m.cross_chain_alternates);
  if (alternates && alternates.length) {
    const altPairs = alternates.map((pair) => {
      let chainCode, altKey;
      if (Array.isArray(pair)) {
        [chainCode, altKey] = pair;
      } else if (pair && typeof pair.get === "function") {
        chainCode = pair.get(0); altKey = pair.get(1);
      } else if (pair && typeof pair === "object") {
        chainCode = pair[0]; altKey = pair[1];
      } else {
        chainCode = "?"; altKey = String(pair);
      }
      return [chainCode, altKey];
    });

    const copyAllBtn = makeCopyButton(() =>
      altPairs.map(([chainCode, altKey]) => chainCode + ": " + altKey).join("\n")
    );
    copyAllBtn.textContent = "Copy all";
    copyAllBtn.classList.add("match-card__copy-all");

    card.appendChild(renderCollapsible(
      "Cross-chain alternates (" + alternates.length + ")",
      () => {
        const body = document.createElement("div");
        for (const [chainCode, altKey] of altPairs) {
          const row = document.createElement("div");
          row.className = "match-card__alt";
          const code = document.createElement("code");
          code.textContent = chainCode;
          const val = document.createElement("span");
          val.style.wordBreak = "break-all";
          val.textContent = altKey;
          const cpy = makeCopyButton(() => altKey);
          row.appendChild(code);
          row.appendChild(val);
          row.appendChild(cpy);
          body.appendChild(row);
        }
        return body;
      },
      copyAllBtn
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

function renderMaskedKey(span, raw, globalUnmask) {
  const sensitive = span.dataset.sensitive === "1";
  span.textContent = "";
  if (!sensitive) {
    span.textContent = raw;
    return;
  }
  span.dataset.raw = raw;
  // Global unmask = on: render unmasked, skip the per-card button (redundant).
  if (globalUnmask) {
    span.dataset.unmasked = "1";
    span.appendChild(document.createTextNode(raw));
    return;
  }
  span.dataset.unmasked = "0";
  span.appendChild(document.createTextNode(maskValue(raw)));
  span.appendChild(makeUnmaskButton(span, raw));
}

function makeUnmaskButton(span, raw) {
  const btn = document.createElement("button");
  btn.className = "match-card__unmask";
  btn.textContent = "unmask";
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (span.dataset.unmasked === "1") return;
    const ok = window.confirm(
      "This will display a sensitive key in plaintext.\n\n" +
      "Make sure no one is shoulder-surfing and you don't have a screen recorder running.\n\n" +
      "Continue?"
    );
    if (!ok) return;
    span.dataset.unmasked = "1";
    span.textContent = "";
    span.appendChild(document.createTextNode(raw));
    span.appendChild(makeMaskButton(span, raw));
  });
  return btn;
}

function makeMaskButton(span, raw) {
  const btn = document.createElement("button");
  btn.className = "match-card__unmask";
  btn.textContent = "mask";
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    span.dataset.unmasked = "0";
    span.textContent = "";
    span.appendChild(document.createTextNode(maskValue(raw)));
    span.appendChild(makeUnmaskButton(span, raw));
  });
  return btn;
}

function maskValue(raw) {
  if (!raw) return "";
  if (raw.length <= 12) {
    return raw.slice(0, 2) + "…" + raw.slice(-2) + " (" + (raw.length - 4) + " chars masked)";
  }
  return raw.slice(0, 4) + "…" + raw.slice(-4) + " (" + (raw.length - 8) + " chars masked)";
}

function makeCopyButton(valueFn) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "match-card__copy";
  btn.textContent = "copy";
  btn.setAttribute("aria-label", "Copy to clipboard");
  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const value = valueFn();
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Legacy / non-secure-context fallback.
      const ta = document.createElement("textarea");
      ta.value = value;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch {}
      document.body.removeChild(ta);
    }
    const prev = btn.textContent;
    btn.textContent = "✓";
    btn.classList.add("match-card__copy--done");
    setTimeout(() => {
      btn.textContent = prev;
      btn.classList.remove("match-card__copy--done");
    }, 800);
  });
  return btn;
}

function renderCollapsible(title, bodyFactory, headerExtra) {
  const sec = document.createElement("div");
  sec.className = "match-card__section";
  // <button> (not <p>) so the toggle is keyboard-activatable + screen-reader-announced.
  const t = document.createElement("button");
  t.type = "button";
  t.className = "match-card__section-title";
  t.setAttribute("aria-expanded", "true");
  const label = document.createElement("span");
  label.className = "match-card__section-title-text";
  label.textContent = title;
  t.appendChild(label);
  if (headerExtra) t.appendChild(headerExtra);
  sec.appendChild(t);
  const body = document.createElement("div");
  body.className = "match-card__section-body";
  body.appendChild(bodyFactory());
  sec.appendChild(body);
  t.addEventListener("click", () => {
    const willOpen = !sec.classList.contains("match-card__section--open");
    sec.classList.toggle("match-card__section--open", willOpen);
    t.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });
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

function initUnmaskToggle() {
  const toggle = els.unmaskToggle;
  if (!toggle) return;
  // The browser flips the checkbox state before our click handler fires.
  // We intercept the flip: if it's the OFF→ON transition, we cancel, run the
  // three confirms, and set the final state ourselves.
  toggle.addEventListener("click", () => {
    if (!toggle.checked) {
      // User just turned it OFF — instant, no confirm. Let the change handler do the rest.
      return;
    }
    // User just turned it ON — undo immediately, then re-check only if they pass 3 confirms.
    toggle.checked = false;
    const ok =
      window.confirm("Revealing keys will display private keys in plaintext. Continue?") &&
      window.confirm("Are you sure? Shoulder-surfing and screen recording risks apply.") &&
      window.confirm("Final confirmation: display all keys unmasked?");
    if (ok) {
      toggle.checked = true;
    }
  });
  toggle.addEventListener("change", () => {
    showUnmaskBanner(toggle.checked);
  });
  // Restore banner visibility if the toggle was somehow left on across re-render.
  showUnmaskBanner(toggle.checked);
}

function showUnmaskBanner(visible) {
  if (els.unmaskBanner) els.unmaskBanner.hidden = !visible;
}

els.classifyBtn.addEventListener("click", classifyAndRender);

// ===== Keyboard shortcuts =====
function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT" || el.isContentEditable;
}

document.addEventListener("keydown", (e) => {
  // Cmd/Ctrl+Enter → classify (works anywhere on the page).
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    classifyAndRender();
    return;
  }
  // Cmd/Ctrl+K → focus + select the key input.
  if (e.key.toLowerCase() === "k" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    els.input.focus();
    els.input.select();
    return;
  }
  // ? → toggle the shortcuts overlay (only when NOT typing in an input).
  if (e.key === "?" && !isTypingTarget(e.target)) {
    e.preventDefault();
    toggleOverlay(els.shortcutsOverlay);
    return;
  }
  // ESC → close the overlay (if open) OR close the history popover.
  if (e.key === "Escape") {
    if (els.shortcutsOverlay && !els.shortcutsOverlay.hidden) {
      closeOverlay(els.shortcutsOverlay);
      return;
    }
    if (els.historyPopover && !els.historyPopover.hidden) {
      closeHistoryPopover();
      return;
    }
  }
});

function toggleOverlay(overlay) {
  if (!overlay) return;
  if (overlay.hidden) openOverlay(overlay);
  else closeOverlay(overlay);
}

function openOverlay(overlay) {
  if (!overlay || !overlay.hidden) return;
  overlay.hidden = false;
  // Focus trap: remember what had focus, then move it to the first focusable.
  overlay._lastFocus = document.activeElement;
  const focusables = overlay.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (focusables.length) focusables[0].focus();
  // Trap Tab within the overlay.
  overlay._tabTrap = (e) => {
    if (e.key !== "Tab" || overlay.hidden) return;
    const items = Array.from(
      overlay.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => !el.disabled && el.offsetParent !== null);
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };
  overlay.addEventListener("keydown", overlay._tabTrap);
}

function closeOverlay(overlay) {
  if (!overlay || overlay.hidden) return;
  overlay.hidden = true;
  if (overlay._tabTrap) {
    overlay.removeEventListener("keydown", overlay._tabTrap);
    overlay._tabTrap = null;
  }
  if (overlay._lastFocus && typeof overlay._lastFocus.focus === "function") {
    overlay._lastFocus.focus();
    overlay._lastFocus = null;
  }
}

function initKeyboardShortcuts() {
  // Wire overlay close buttons (backdrop + explicit Close button share data-close-overlay).
  if (els.shortcutsOverlay) {
    els.shortcutsOverlay.querySelectorAll("[data-close-overlay]").forEach((el) => {
      el.addEventListener("click", () => closeOverlay(els.shortcutsOverlay));
    });
  }
}

// ===== Share button =====
function initShareButton() {
  if (!els.shareBtn) return;
  els.shareBtn.addEventListener("click", async () => {
    const hash = buildShareHash();
    if (!hash) return;
    const url = location.origin + location.pathname + location.search + hash;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Legacy fallback for non-secure contexts.
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch {}
      document.body.removeChild(ta);
    }
    const prev = els.shareBtn.textContent;
    els.shareBtn.textContent = "Copied!";
    setTimeout(() => { els.shareBtn.textContent = prev; }, 1200);
  });
}

// ===== Download JSON =====
function updateDownloadBtn() {
  if (!els.downloadBtn) return;
  els.downloadBtn.disabled = !lastResults;
}

function initDownloadButton() {
  if (!els.downloadBtn) return;
  els.downloadBtn.addEventListener("click", () => {
    if (!lastResults) return;
    const json = JSON.stringify(lastResults, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const stamp =
      d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
      "-" + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
    a.href = url;
    a.download = "ckc-results-" + stamp + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Revoke on a tick so the download has time to start.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}

// ===== History popover =====
function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(entries) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch {
    /* localStorage quota / disabled — silent */
  }
}

function addToHistory(value) {
  if (!value || !value.trim()) return;
  const entry = { value, ts: Date.now() };
  let entries = loadHistory();
  // Dedup: if the exact value already exists, drop the older entry so the new
  // one floats to the top with a fresh timestamp.
  entries = entries.filter((e) => e.value !== value);
  entries.unshift(entry);
  if (entries.length > HISTORY_MAX) entries = entries.slice(0, HISTORY_MAX);
  saveHistory(entries);
  updateHistoryBtn();
  // If the popover is open, refresh its contents.
  if (els.historyPopover && !els.historyPopover.hidden) renderHistoryPopover();
}

function maskForHistory(value) {
  // First 8 + … + last 4. Used for display-only in the popover list.
  if (!value) return "";
  // For multi-line bulk entries, show the first line masked + count.
  const lines = value.split(/\r\n|\r|\n/).filter((l) => l.trim().length > 0);
  if (lines.length > 1) {
    const first = lines[0];
    const masked = first.length <= 12
      ? first.slice(0, 2) + "…" + first.slice(-2)
      : first.slice(0, 8) + "…" + first.slice(-4);
    return masked + " (+" + (lines.length - 1) + " more)";
  }
  const v = value;
  if (v.length <= 12) return v.slice(0, 2) + "…" + v.slice(-2);
  return v.slice(0, 8) + "…" + v.slice(-4);
}

function formatHistoryTime(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    pad(d.getMonth() + 1) + "/" + pad(d.getDate()) +
    " " + pad(d.getHours()) + ":" + pad(d.getMinutes())
  );
}

function updateHistoryBtn() {
  if (!els.historyBtn) return;
  const count = loadHistory().length;
  els.historyBtn.textContent = count > 0 ? "History (" + count + ")" : "History";
  els.historyBtn.disabled = count === 0;
}

function renderHistoryPopover() {
  const pop = els.historyPopover;
  if (!pop) return;
  pop.innerHTML = "";
  const entries = loadHistory();
  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "history-popover__empty";
    empty.textContent = "No classifications yet.";
    pop.appendChild(empty);
    return;
  }
  const list = document.createElement("div");
  list.className = "history-popover__list";
  list.setAttribute("role", "list");
  for (const e of entries) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "history-popover__item";
    item.setAttribute("role", "listitem");
    const val = document.createElement("span");
    val.className = "history-popover__item-value";
    val.textContent = maskForHistory(e.value);
    const time = document.createElement("span");
    time.className = "history-popover__item-time";
    time.textContent = formatHistoryTime(e.ts);
    item.appendChild(val);
    item.appendChild(time);
    item.addEventListener("click", () => {
      els.input.value = e.value;
      updateBulkIndicator();
      syncHashFromState();
      closeHistoryPopover();
      els.input.focus();
    });
    list.appendChild(item);
  }
  pop.appendChild(list);

  const footer = document.createElement("div");
  footer.className = "history-popover__footer";
  const clear = document.createElement("button");
  clear.type = "button";
  clear.className = "btn btn--ghost btn--sm";
  clear.textContent = "Clear history";
  clear.addEventListener("click", () => {
    if (!window.confirm("Clear all classification history? This cannot be undone.")) return;
    saveHistory([]);
    renderHistoryPopover();
    updateHistoryBtn();
    closeHistoryPopover();
  });
  footer.appendChild(clear);
  pop.appendChild(footer);
}

function openHistoryPopover() {
  const pop = els.historyPopover;
  const btn = els.historyBtn;
  if (!pop || !btn) return;
  renderHistoryPopover();
  pop.hidden = false;
  btn.setAttribute("aria-expanded", "true");
  // Click-outside to close.
  document.addEventListener("click", historyOutsideClick, true);
}

function closeHistoryPopover() {
  const pop = els.historyPopover;
  const btn = els.historyBtn;
  if (!pop) return;
  pop.hidden = true;
  if (btn) btn.setAttribute("aria-expanded", "false");
  document.removeEventListener("click", historyOutsideClick, true);
}

function historyOutsideClick(e) {
  const pop = els.historyPopover;
  const btn = els.historyBtn;
  if (!pop || pop.hidden) return;
  if (pop.contains(e.target) || (btn && btn.contains(e.target))) return;
  closeHistoryPopover();
}

function initHistoryPopover() {
  if (!els.historyBtn) return;
  els.historyBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (els.historyPopover.hidden) openHistoryPopover();
    else closeHistoryPopover();
  });
}
