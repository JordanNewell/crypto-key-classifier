"""Parse argv / stdin / file inputs and route them through the classify pipeline.

Usage:
  classify-key <INPUT>
  classify-key <INPUT1> <INPUT2> ...     (batch → terse)
  classify-key --file keys.txt           (batch → terse)
  echo "<input>" | classify-key          (stdin)
  classify-key --json <INPUT>
  classify-key --no-mask --no-cross-chain <INPUT>
"""

from __future__ import annotations

import argparse
import sys

from ckc.pipeline import Config, classify
from ckc.reporter import render_json_array, render_rich, render_terse


def _ensure_utf8_stdout() -> None:
    """Force UTF-8 on stdout/stderr so unicode glyphs (✓, →, •) render on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="classify-key",
        description="Classify any crypto-key string (BTC/ETH/SOL/Cosmos + more) "
                    "with aggressive recovery from corruption.",
    )
    p.add_argument("inputs", nargs="*", help="input string(s) to classify")
    p.add_argument("--file", "-f", help="read inputs from file (one per line)")
    p.add_argument(
        "--rich", action="store_true", help="rich multi-line output (default for 1 input)"
    )
    p.add_argument("--terse", action="store_true", help="one-line output (default for 2+ inputs)")
    p.add_argument("--json", dest="as_json", action="store_true", help="JSON output")
    p.add_argument("--no-mask", action="store_true", help="show full private keys (DANGEROUS)")
    p.add_argument("--no-cross-chain", action="store_true", help="omit cross-chain alternates")
    p.add_argument("--no-wallets", action="store_true", help="omit wallet compatibility list")
    p.add_argument("--explain", action="store_true", help="include repair trace")
    p.add_argument("--min-confidence", type=int, default=0, help="filter matches below N%%")
    p.add_argument("--chains", help="comma-separated chain whitelist (e.g. btc,eth,sol)")
    return p


def _gather_inputs(args: argparse.Namespace) -> tuple[list[str], str | None]:
    """Collect inputs from positional args, --file, and stdin.

    Returns (inputs, error). When error is non-None the CLI prints it to
    stderr and exits 2 — never raises, so callers don't see raw tracebacks
    for missing/unreadable files.
    """
    inputs: list[str] = list(args.inputs)
    if args.file:
        try:
            f = open(args.file, encoding="utf-8")
        except OSError as e:
            return [], f"error: cannot open --file {args.file!r}: {e.strerror or e}"
        with f:
            inputs.extend(
                line.strip() for line in f if line.strip() and not line.startswith("#")
            )
    if not sys.stdin.isatty() and not inputs:
        for line in sys.stdin:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                inputs.append(stripped)
    return inputs, None


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    args = _build_parser().parse_args(argv)
    inputs, file_err = _gather_inputs(args)

    if file_err:
        print(file_err, file=sys.stderr)
        return 2

    if not inputs:
        print("error: no input provided", file=sys.stderr)
        return 2

    chains_whitelist = (
        {c.strip().upper() for c in args.chains.split(",") if c.strip()}
        if args.chains
        else None
    )
    config = Config(
        chains=chains_whitelist,
        min_confidence=args.min_confidence,
    )

    is_batch = len(inputs) > 1
    mask = not args.no_mask

    # Warn on --no-mask with potential private keys
    if args.no_mask:
        print(
            "WARNING: --no-mask is on. If any input is a private key, "
            "it will be printed to stdout in cleartext.",
            file=sys.stderr,
        )

    results = [(raw, classify(raw, config=config)) for raw in inputs]

    # JSON mode: emit a single array wrapping all results so the documented
    # `jq '.[] | .best_guess'` pipeline works for both single and batch input.
    if args.as_json:
        print(render_json_array(results, mask_private_keys=mask))
        return 0

    for raw, matches in results:
        if args.rich or not (is_batch or args.terse):
            # Single input default → rich
            print(
                render_rich(
                    raw, matches,
                    mask_private_keys=mask,
                    show_wallets=not args.no_wallets,
                    show_cross_chain=not args.no_cross_chain,
                    explain=args.explain,
                )
            )
        else:
            # Batch default → terse
            print(render_terse(raw, matches, mask_private_keys=mask))

    return 0


if __name__ == "__main__":
    sys.exit(main())
