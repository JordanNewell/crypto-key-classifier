# Security Policy

## Reporting a vulnerability

Email **security@jordannewell.com** with a description of the issue, the
steps to reproduce, the affected version (`classify-key --version`), and
any suggested fix.

A PGP key is not configured for this address yet. If you need to send an
encrypted report, say so in your first email and we will arrange a key
exchange out of band.

**Do not open a public GitHub issue** for security reports.

## Response timeline

| Step | Target |
|---|---|
| Acknowledge receipt | within 72 hours |
| Initial assessment | within 7 days |
| Fix or mitigation | within 30 days (severity-dependent) |
| Coordinated public disclosure | after fix ships, or 90 days (whichever first) |

## What to include

- Description of the issue and potential impact
- Step-by-step reproduction (CLI invocation + input)
- Affected version (`classify-key --version`)
- Optional: suggested fix or patch

## What NOT to include

**Never include real mainnet private keys, seed phrases, or wallet
imports in a bug report.** This tool is designed to operate on sensitive
key material — your report does not need to. Use the public test vectors
in [`tests/fixtures/`](tests/fixtures/) or generate a fresh throwaway key.

## Scope

In scope:

- The `crypto-key-classifier` source tree (`src/ckc/`, CLI entry point,
  test fixtures, build config)
- The `classify-key` CLI behavior — input handling, output masking,
  file/stdin handling, the repair pipeline's interaction with untrusted
  input
- The demo site at
  <https://jordannewell.github.io/crypto-key-classifier/> (Pyodide build,
  in-browser key handling, client-side behavior)

Out of scope:

- Vulnerabilities in upstream dependencies (`base58`, `pycryptodome`,
  Pyodide, etc.) — report those to the upstream project
- Issues that require the user to deliberately defeat safety guards
  (e.g., piping `--no-mask` output to a public log)

## Trust boundary

`classify-key` is **offline by design**. It makes zero network calls and
writes nothing to disk unless the user explicitly redirects output. The
demo site runs entirely client-side via Pyodide — keys never leave the
browser. Any report claiming network exfiltration will be verified
against this invariant before acceptance.
