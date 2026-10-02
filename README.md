# PR Audit

[![PyPI](https://img.shields.io/pypi/v/pr-audit)](https://pypi.org/project/pr-audit/)
[![Python](https://img.shields.io/pypi/pyversions/pr-audit)](https://pypi.org/project/pr-audit/)
[![CI](https://github.com/cabusto/pr-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/cabusto/pr-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

PR Audit is a deterministic, local-first CLI for orienting yourself in a Python pull request.

It compares two Git refs, classifies the changed files, analyzes dependency and Python function changes, and writes a stable audit in:

- `audit.json`
- `audit.md`

It is meant to help a reviewer decide where to start, not to judge whether the change is good or bad.

## Why PR Audit

Tools like radon, complexipy and diff-cover measure files or coverage. PR Audit is scoped to a single pull request: it answers "what changed, how big is it, and where should I look first?"

- **Reviewers** get a short, ranked list of hotspots instead of scrolling a large diff top to bottom.
- **Authors** see the complexity and nesting they added before asking for review.
- **Maintainers** spot new runtime dependencies and production changes that arrive without tests.

The output is deterministic, so the same refs always produce the same audit. It needs no network access and no third-party dependencies, and it never executes the code under review. Python files are parsed with `ast`.

## Install

```bash
python3 -m pip install pr-audit
```

To work on PR Audit itself, install from a clone:

```bash
python3 -m pip install -e .
```

## Run

```bash
pr-audit analyze
```

By default, the CLI infers the base ref from the repo's default branch
(`origin/HEAD`, `origin/main`, `main`, and a few common fallbacks).

If you need an explicit range, use:

```bash
pr-audit analyze --base main --head HEAD
```

You can also run it as a module:

```bash
python3 -m pr_audit analyze
```

## Output

By default, files are written to the current directory.

```bash
pr-audit analyze --base main --head HEAD --output out/
```

Use `--format json`, `--format markdown`, or `--format both`.

## Help

```bash
pr-audit --help
pr-audit analyze --help
```

## GitHub Action

PR Audit ships as a composite action. The audit is written to the job summary and to `pr-audit-out/`.

```yaml
name: PR Audit

on:
  pull_request:

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: cabusto/pr-audit@v1
```

| Input | Default | Meaning |
| --- | --- | --- |
| `base` | PR base SHA | Base ref to compare from |
| `head` | PR head SHA | Head ref to compare to |
| `format` | `both` | `markdown`, `json` or `both` |
| `output` | `pr-audit-out` | Output directory |
| `python-version` | `3.12` | Python used to run pr-audit |
| `step-summary` | `true` | Append `audit.md` to the job summary |

The action exposes `markdown-path` and `json-path` outputs.

### Posting the audit as a PR comment

To comment on pull requests, including those from forks, keep the analysis job read-only and post the comment from a separate `workflow_run` workflow. This repository does this for its own PRs:

- [`.github/workflows/pr-audit.yml`](.github/workflows/pr-audit.yml) runs on non-draft PRs with read-only permissions, then uploads the audit as an artifact.
- [`.github/workflows/pr-audit-comment.yml`](.github/workflows/pr-audit-comment.yml) runs after it, downloads the artifact, and creates or updates a single bot comment.

Copy both files to use the same setup.

## Example

This is the real audit of the commit that added structural metrics to PR Audit itself:

```bash
$ pr-audit analyze --base 1dd873b --head 69af933
Analyzing 1dd873b...69af933
✓ 11 changed files
✓ dependencies analyzed
✓ Python functions analyzed
✓ audit.json
✓ audit.md
```

<details>
<summary>Generated <code>audit.md</code></summary>

```md
# PR Audit

## Scope
+425 / -48 LOC
11 files changed · 2 added · 0 deleted

Production  8
Tests       3
Config      0
Docs        0
Dependency  0
Other       0

## Dependencies
No dependency manifest changes detected

## Tests
3 test files changed · 1 added
204 test LOC added
221 production LOC added
Production:test LOC ratio 1.1:1

## Structure
Production files
1 added · 7 modified · 0 deleted

Python structure
3 classes added
9 functions/methods added
1 function/method removed

## Complexity
4 changed functions increased in complexity

src/pr_audit/scoring/hotspots.py: score_hotspots
LOC         66 -> 80
Complexity   33 -> 45
Nesting      3 -> 3

src/pr_audit/analysis.py: analyze_repo
LOC         78 -> 103
Complexity   17 -> 22
Nesting      3 -> 7

src/pr_audit/render/markdown.py: _render_hotspots
LOC         24 -> 26
Complexity   9 -> 10
Nesting      2 -> 3

src/pr_audit/analyzers/functions.py: analyze_changed_python_file
LOC         46 -> 47
Complexity   22 -> 23
Nesting      2 -> 2

## Review hotspots
HIGH  src/pr_audit/scoring/hotspots.py
      +39 / -30 LOC
      Largest production change in this PR
      Complexity +12

HIGH  src/pr_audit/analysis.py
      +27 / -2 LOC
      Complexity +5
      Max nesting +4

MED   src/pr_audit/render/markdown.py
      +67 / -2 LOC
      Largest production change in this PR
      Complexity +1
      Max nesting +1

MED   src/pr_audit/analyzers/structure.py
      +59 LOC
      New production file

LOW   src/pr_audit/analyzers/functions.py
      +3 / -2 LOC
      Complexity +1
```

</details>

## What it reports

- Scope metrics
- File classification
- Dependency changes from `pyproject.toml` and `requirements.txt`
- Test vs production LOC
- Changed Python functions, shown as `file.py: function`
- Cyclomatic complexity and nesting
- Deterministic review hotspots

Cyclomatic complexity is a rough count of the independent control-flow paths in a function. It increases with branches, loops, `except` blocks, boolean operators, ternaries, and `match` cases. Higher numbers mean more paths to reason about, not necessarily bad code.

Nesting depth is the deepest level of nested control flow inside the function.

## Stable metrics

These are the stable metric names used by the underlying audit model.

| Metric | Meaning |
| --- | --- |
| `pr.loc.added` | Total added LOC across the audit |
| `pr.loc.deleted` | Total deleted LOC across the audit |
| `pr.files.changed` | Total changed files |
| `pr.files.added` | Total added files |
| `pr.files.deleted` | Total deleted files |
| `dependency.runtime.added` | Runtime dependencies added in supported manifests |
| `dependency.runtime.removed` | Runtime dependencies removed in supported manifests |
| `dependency.runtime.changed` | Runtime dependency version changes |
| `tests.files.changed` | Changed files classified as tests |
| `tests.files.added` | Added files classified as tests |
| `tests.loc.added` | Added LOC in test files |
| `complexity.cyclomatic.max.before` | Highest cyclomatic complexity before the change |
| `complexity.cyclomatic.max.after` | Highest cyclomatic complexity after the change |
| `complexity.nesting.max.before` | Highest nesting depth before the change |
| `complexity.nesting.max.after` | Highest nesting depth after the change |

## Development

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests
```

Release notes are in [CHANGELOG.md](CHANGELOG.md). Publishing a GitHub Release uploads the package to PyPI through trusted publishing.

## License

[MIT](LICENSE)
