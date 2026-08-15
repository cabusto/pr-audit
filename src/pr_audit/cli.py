from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

from .analysis import analyze_repo
from .errors import GitCommandError, InvalidGitRefError, OutputError, PrAuditError
from .git import git_toplevel, infer_base_ref
from .render import render_json, render_markdown


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pr-audit",
        description="Deterministic pull-request audit for local Git refs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              pr-audit analyze
              pr-audit analyze --base main --head HEAD
              pr-audit analyze --base main --head HEAD --format json --output out/
            """
        ).strip(),
    )
    subparsers = parser.add_subparsers(dest="command")
    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze a PR range",
        description="Analyze changes between two local Git refs.",
    )
    analyze.add_argument(
        "--base",
        default=None,
        help="Base Git ref to compare from (default: inferred from the repo's default branch)",
    )
    analyze.add_argument("--head", default="HEAD", help="Head Git ref to compare to (default: HEAD)")
    analyze.add_argument(
        "--format",
        choices=("markdown", "json", "both"),
        default="both",
        help="Output format to write (default: both)",
    )
    analyze.add_argument(
        "--output",
        default=None,
        help="Directory to write audit.json and/or audit.md into (default: current directory)",
    )
    return parser


def _write_outputs(output_dir: Path, output_format: str, json_text: str, markdown_text: str) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    if output_format in {"json", "both"}:
        (output_dir / "audit.json").write_text(json_text, encoding="utf-8")
        written.append("audit.json")
    if output_format in {"markdown", "both"}:
        (output_dir / "audit.md").write_text(markdown_text, encoding="utf-8")
        written.append("audit.md")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command != "analyze":
        parser.print_help()
        return 0

    cwd = Path.cwd()
    try:
        repo_root = git_toplevel(cwd)
        base_ref = args.base or infer_base_ref(repo_root)
        audit = analyze_repo(repo_root, base_ref, args.head)
        output_dir = Path(args.output) if args.output else cwd
        if not output_dir.is_absolute():
            output_dir = (cwd / output_dir).resolve()
        if output_dir.exists() and not output_dir.is_dir():
            raise OutputError(f"Output path is not a directory: {output_dir}")
        json_text = render_json(audit)
        markdown_text = render_markdown(audit)
        written = _write_outputs(output_dir, args.format, json_text, markdown_text)
        print(f"Analyzing {base_ref}...{args.head}")
        print(f"✓ {audit.scope.files_changed} changed files")
        print("✓ dependencies analyzed")
        print("✓ Python functions analyzed")
        for filename in written:
            print(f"✓ {filename}")
        return 0
    except PrAuditError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
