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

function applyHashExample() {
  const hash = window.location.hash || "";
  const match = hash.match(/^#example=(.+)$/);
  if (!match) return;
  const slug = decodeURIComponent(match[1]);
  const opt = findOptionBySlug(slug);
  if (!opt) return;
  els.exampleSelect.value = opt.value;
  els.input.value = opt.value;
  const ex = (examplesCache || []).find((x) => x.value === opt.value);
  if (ex && ex.note) {
    els.exampleNote.textContent = ex.note;
    els.exampleNote.hidden = false;
  }
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
  applyHashExample();
  return examplesCache;
}

function init() {
  els.classifyBtn.disabled = true;
  els.clearBtn.addEventListener("click", () => {
    els.input.value = "";
    els.results.innerHTML = "";
    els.exampleSelect.value = "";
    els.exampleNote.hidden = true;
    if (window.location.hash) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    els.input.focus();
  });
  els.exampleSelect.addEventListener("change", (e) => {
    const value = e.target.value;
    const selected = e.target.options[e.target.selectedIndex];
    const slug = selected && selected.dataset.slug;
    if (!value) {
      els.exampleNote.hidden = true;
      if (window.location.hash) {
        history.replaceState(null, "", window.location.pathname + window.location.search);
      }
      return;
    }
    els.input.value = value;
    // Sync URL hash so the URL is shareable for this example.
    history.replaceState(null, "", "#example=" + encodeURIComponent(slug));
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

// ===== Classify + render =====

function classifyAndRender() {
  // Don't trim — classify()'s preprocessor handles whitespace, confusables, etc.
  // Trimming here would mask the very repair features the demo exists to show off.
  const input = els.input.value;
  els.results.innerHTML = "";
  if (!input || !input.trim()) return;

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

  // Input row (masked if sensitive)
  const keyRow = document.createElement("div");
  keyRow.className = "match-card__row";
  const keyLabel = document.createElement("span");
  keyLabel.textContent = "input";
  const keySpan = document.createElement("span");
  keySpan.className = "match-card__key";
  keySpan.dataset.sensitive = isSensitive(m) ? "1" : "0";
  renderMaskedKey(keySpan, els.input.value);
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

function renderMaskedKey(span, raw) {
  const sensitive = span.dataset.sensitive === "1";
  span.textContent = "";
  if (!sensitive) {
    span.textContent = raw;
    return;
  }
  span.dataset.raw = raw;
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

els.classifyBtn.addEventListener("click", classifyAndRender);
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    classifyAndRender();
  }
});
