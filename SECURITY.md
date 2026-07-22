# Security Policy

## Reporting a vulnerability

Email **security@jordannewell.com**. PGP-encrypted reports are welcome —
locate the key via Web Key Directory:

```bash
gpg --auto-key-locate clear,dkd,nodefault --locate-key jordan@jordannewell.com
```

Fingerprint: `67567DC5E7C5353F85F2AF0DAC05D3F3E0EFA32A` (Ed25519, see
[`SIGNATURE.md`](SIGNATURE.md) for full details).

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

- `classify-key` CLI behavior
- The `ckc` Python package (`src/ckc/`)
- Output masking, file handling, stdin handling
- The repair pipeline's interaction with untrusted input

Out of scope:

- Vulnerabilities in upstream dependencies (`base58`, `pycryptodome`) —
  report those to the upstream project
- Issues that require the user to deliberately defeat safety guards
  (e.g., piping `--no-mask` output to a public log)

## Trust boundary

`classify-key` is **offline by design**. It makes zero network calls and
writes nothing to disk unless the user explicitly redirects output. Any
report claiming network exfiltration will be verified against this
invariant before acceptance.
