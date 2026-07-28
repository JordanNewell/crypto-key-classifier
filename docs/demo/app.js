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
