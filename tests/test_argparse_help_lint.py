"""Lint: scan all add_argument() calls for bare '%' in help= strings.

Regression guard for the argparse footgun where a literal '%' in a help
string causes 'ValueError: incomplete format' at --help render time.
Argparse uses printf-style substitution (%(default)s etc.), so every
literal '%' must be escaped as '%%'.

Detection: Python's own '%' operator is the oracle. A string with a bare
'%' raises ValueError: incomplete format when formatted with ().
That's exactly the error argparse hits when rendering --help.

This test walks all Python files under src/ with AST, finds add_argument()
calls, inspects help= keyword args, and asserts each string formats cleanly.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _find_argparse_help_strings(tree: ast.AST) -> list[str]:
    """Walk AST, return all help= string literals from add_argument() calls."""
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument":
            continue
        for kw in node.keywords:
            if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, str):
                    out.append(kw.value.value)
    return out


def _has_bare_percent(s: str) -> bool:
    """True if Python's % operator would raise ValueError on this string.

    That's the exact condition that breaks argparse --help rendering.
    Other format specs (like %s with too-few args) raise TypeError, which
    argparse handles fine — we ignore those.
    """
    try:
        s % ()
        return False
    except ValueError:
        return True  # incomplete format — bare %
    except TypeError:
        return False  # other format specs are OK


def _src_python_files() -> list[Path]:
    root = Path(__file__).parent.parent / "src"
    return list(root.rglob("*.py"))


def test_no_bare_percent_in_argparse_help():
    """All argparse help= strings must format cleanly with % operator."""
    violations: list[str] = []
    for path in _src_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for help_str in _find_argparse_help_strings(tree):
            if _has_bare_percent(help_str):
                violations.append(
                    f"{path.relative_to(path.parents[-1])}: "
                    f"help={help_str!r} contains bare '%' — escape as '%%'"
                )
    assert not violations, (
        f"{len(violations)} argparse help string(s) with bare '%' found:\n  "
        + "\n  ".join(violations)
    )
