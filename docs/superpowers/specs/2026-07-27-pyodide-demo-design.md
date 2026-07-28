# crypto-key-classifier — Pyodide web demo

**Date:** 2026-07-27
**Status:** Approved (brainstorm)
**Project:** `crypto-key-classifier` v0.6.1
**Owner:** Jordan Newell

## Goal

Ship a single-page interactive demo at `https://jordannewell.github.io/crypto-key-classifier/` where visitors paste a crypto-key string and the actual `ckc` package classifies it in-browser via Pyodide. Zero server. Zero network calls. The key never leaves the visitor's browser.

## Why

- **Discoverable proof.** README shows terminal screenshots; a live demo converts "trust me" into "try it." Higher confidence for the recovery / forensics / triage audience.
- **Differentiator.** The Cosmos 20-chain HRP swap and the OCR repair trace are the two killer features. Both land harder when a visitor can paste their own key and watch them fire.
- **Brand consistency.** Matches the BLACK + WHITE + NEON GREEN (#00FF00) JordanNewell brand applied across the rest of the portfolio.

## Non-goals

- No multi-page docs site (mkdocs/Astro). One page.
- No automated browser tests this pass. Manual smoke only.
- No server-side anything. Pure static.
- No demo of `--no-mask`. Masking is always on by default for safety.
- No version auto-tracking. Demo is pinned to `crypto-key-classifier==0.6.1`.

## Architecture

Approach **A** from brainstorm: Pyodide + `micropip.install` from PyPI.

```
docs/demo/
  index.html        Page shell: hero, input panel, results panel, footer
  app.js            Pyodide boot, classify() wiring, render
  styles.css        Brutalist neon-green (brand)
  examples.json     6 preset public test vectors for "Load example"
.github/workflows/
  pages.yml         Deploy docs/demo → GitHub Pages on push to main
```

No build step. No framework. Three static files + one CI workflow.

### Pyodide boot flow

1. Page paints with branded loader overlay ("Booting Python…").
2. `<script src="https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js">`.
3. `await loadPyodide()` → `await pyodide.loadPackage("micropip")`.
4. `await pyodide.runPythonAsync('import micropip; await micropip.install("crypto-key-classifier==0.6.1")')`.
   - Pulls `pycryptodome` from Pyodide's curated package set.
   - Pulls `base58` (pure Python) from PyPI.
   - Pulls `crypto-key-classifier` (pure Python) from PyPI.
5. `window.classify = pyodide.pyimport("ckc.pipeline").classify`.
6. Hide loader, enable Classify button.
7. Expected cold-start: 3–8 seconds.

### Runtime call

On submit:

```js
const matches = window.classify(inputText).toJs();
// list[Match], sorted by confidence desc on the Python side
```

`classify` takes only the raw string (the `Config` second arg exists but only controls `chains` / `min_confidence` filtering — we don't need either this pass). `explain` is a **reporter** concern, not a pipeline one — every `Match` already carries `repairs_applied: list[str]` regardless of how it's invoked. The "Show repair trace" toggle is a pure UI decision: render or hide that field.

`Match` does **not** contain the raw key string — it carries `chain`, `format`, `key_type`, `confidence`, `checksum_status`, `network`, `cross_chain_alternates: list[tuple[str,str]]`, `wallet_compatibility`, `repairs_applied`, `notes`. The demo masks the input itself in JS based on `key_type ∈ {"private-key", "mnemonic"}` (see Safety / masking below).

## UI surface

### Input panel

- `<textarea>` (monospace, ~80×8) for the key.
- **Classify** button (disabled until Pyodide ready).
- **Show repair trace** checkbox (off by default).
- **Load example** dropdown — 6 presets (see Examples below).
- **Clear** button.

### Result panel

For each `Match`, sorted by `confidence` descending:

- **Chain badge** — chain code in a neon-green-bordered box.
- **Type** — address / private key / mnemonic / view key / etc.
- **Checksum status** — `valid` / `invalid` / `n/a`.
- **Confidence bar** — 0–100%, neon-green fill.
- **Masked key** — `bc1q…wlh (8 chars masked)` by default for sensitive types (`key_type ∈ {"private-key", "mnemonic"}`). Non-sensitive types (`address`, `public-key`) render unmasked. Click to unmask (with confirm dialog if sensitive).
- **Cross-chain alternates** — collapsible list. Only rendered if non-empty (e.g. Cosmos → 20 chains, EVM → 11).
- **Repair trace** — collapsible `<pre>` block. Only rendered if "Show repair trace" was on at submit time.

Empty state: short instruction text. No results: see Error handling.

### Safety banner (sticky, above input)

> 🔒 Your input never leaves your browser. Pyodide runs entirely client-side. No telemetry, no server, no key material transmitted.

Matches the CLI's "zero network calls" promise from the README.

### Branding / visual

- BLACK background (`#000`), WHITE text (`#FFF`), NEON GREEN accents (`#00FF00`).
- Monospace primary font (system stack: `ui-monospace, "SF Mono", "Cascadia Mono", "JetBrains Mono", monospace`).
- Newell wordmark top-left (SVG outline, per `[[reference_newell-in-figma-use-svg-outlines]]`).
- Hero text: `crypto-key-classifier` set in Newell if feasible, else mono uppercase.
- Box-drawing borders (1px neon-green), no rounded corners, no gradients.
- Pixel-art divider per README v2 style (`[[project_readme-v2-brutalist-shipped-2026-07-26]]`).

## Examples (`examples.json`)

Six presets. All **public well-known test vectors** — zero real mainnet keys.

| Label | Source |
|---|---|
| BTC address (bech32) | Bitcoin Wiki `bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq` |
| ETH address | Vitalik's public donation address (EIP-55 checksum demo) |
| Solana pubkey | Solana docs example |
| ATOM address | Cosmos Hub docs example — triggers 20-chain cross-chain |
| Corrupted BTC address | `tests/fixtures/ocr_corrupted.txt` (OCR whitespace + O→0 subs) |
| 12-word mnemonic | BIP-39 spec test vector (`abandon abandon ... about`) |

Each entry: `{"label": "...", "value": "...", "note": "..."}`. `note` shown under dropdown when selected.

## Error handling

| Condition | Response |
|---|---|
| Pyodide fails to load | Red banner: "Browser Python failed to load. [Refresh]." Input disabled. |
| Empty input on submit | Clear results silently. No error. |
| No matches, repair off | "No classifier matched this input. Try enabling 'Show repair trace'." |
| No matches, repair on | "No match even after aggressive recovery. Input may be truncated or wrong charset." |
| Unmask private key / mnemonic | Confirm dialog: "This will display a sensitive key in plaintext. Continue?" |
| Pyodide exception | Red banner with `repr(exc)`. Input stays enabled (Pyodide may still be healthy). |

## Deploy

`.github/workflows/pages.yml`:

- **Trigger:** push to `main` touching `docs/demo/**` or the workflow file itself.
- **Steps:**
  1. Checkout.
  2. `actions/upload-pages-artifact` with `path: docs/demo`.
  3. `actions/deploy-pages` (requires `permissions: pages: write, id-token: write`).
- **Repo Settings → Pages → Source:** GitHub Actions (one-time manual config).
- **URL:** `https://jordannewell.github.io/crypto-key-classifier/`.

## Testing

Manual smoke in browser before declaring done (per `verification-before-completion`):

1. Open deployed URL.
2. Verify branded loader appears, disappears within ~10s.
3. Try each of the 6 examples. Verify chain badge, type, checksum, confidence render correctly.
4. Verify Cosmos example shows 20 cross-chain alternates.
5. Toggle "Show repair trace" on the corrupted-BTC example. Verify trace renders.
6. Try an obviously-invalid input (`hello world`). Verify "no match" path.
7. Verify unmask private-key confirm dialog.
8. Verify safety banner is visible and accurate.

No automated browser tests this pass.

## Risks / known unknowns

- **Pyodide cold-start latency.** 3–8s expected. If it feels too slow, can move to Approach B (pre-built wheel) or C (release-attached wheel) in a follow-up.
- **PyPI downtime** breaks the demo. Mitigation: none this pass; acceptable for a v0 demo.
- **Version drift.** Demo pinned to 0.6.1. New ckc releases don't appear until `app.js` is edited. Acceptable — stable demo > latest demo.
- **`pycryptodome` Pyodide package shape.** Assumed available in Pyodide v0.27.x. If not, fallback is to verify and either pin a different Pyodide version or implement the missing pieces in pure Python.

## Out of scope (future passes)

- Multi-page docs (mkdocs-material or Astro).
- Server-side demo / API.
- Browser automated tests (Playwright).
- "Copy result" buttons, shareable URLs.
- Dark/light toggle (brand is dark-only).
