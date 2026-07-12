"""CLI entry point.

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
from ckc.reporter import render_json, render_rich, render_terse


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
                    "with aggressive recovering from corruption.",
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


def _gather_inputs(args: argparse.Namespace) -> list[str]:
    inputs: list[str] = list(args.inputs)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            inputs.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))
    if not sys.stdin.isatty() and not inputs:
        for line in sys.stdin:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                inputs.append(stripped)
    return inputs


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    args = _build_parser().parse_args(argv)
    inputs = _gather_inputs(args)

    if not inputs:
        print("error: no input provided", file=sys.stderr)
        return 2

    chains_whitelist = set(args.chains.split(",")) if args.chains else None
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

    for raw in inputs:
        matches = classify(raw, config=config)

        # Choose output mode
        if args.as_json:
            print(render_json(raw, matches, mask_private_keys=mask))
        elif args.rich or not (is_batch or args.terse):
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
