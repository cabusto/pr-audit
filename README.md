# PR Audit

### Stop reading pull requests top to bottom. Start where the risk is.

PR Audit reads a Python pull request and tells you, in seconds, **what changed, how big it is, which functions got harder to reason about, and which files to review first.**

Free forever. MIT licensed. No account, no server, no API key, no paid tier waiting around the corner.

[![PyPI](https://img.shields.io/pypi/v/pr-audit)](https://pypi.org/project/pr-audit/)
[![Python](https://img.shields.io/pypi/pyversions/pr-audit)](https://pypi.org/project/pr-audit/)
[![CI](https://github.com/cabusto/pr-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/cabusto/pr-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

```bash
pip install pr-audit && pr-audit analyze
```

---

## This is what your reviewers see

An 11-file, +425 / -48 line PR, boiled down to a reading order. This excerpt is real output from PR Audit's own history:

```text
## Review hotspots
HIGH  src/pr_audit/scoring/hotspots.py
      +39 / -30 LOC
      Largest production change in this PR
      Complexity +12

HIGH  src/pr_audit/analysis.py
      +27 / -2 LOC
      Complexity +5
      Max nesting +4

MED   src/pr_audit/analyzers/structure.py
      +59 LOC
      New production file

## Complexity
src/pr_audit/analysis.py: analyze_repo
LOC         78 -> 103
Complexity   17 -> 22
Nesting      3 -> 7
```

Before you open a single file, you know that `analyze_repo` went from nesting depth 3 to 7. That is the function to read slowly. [See the full audit ↓](#example)

---

## Why teams use it

**⏱ Review faster.** A 40-file diff becomes a ranked list of three or four files that deserve real attention. Reviewers spend their focus where the complexity actually moved, not on renamed imports and fixture churn.

**🔍 Catch what skimming misses.** Nesting that jumped from 3 to 7. A function that doubled in branches. A new runtime dependency tucked into `pyproject.toml`. 200 lines of production code with no test changes. PR Audit surfaces each of these as a number, so none of it hides in the scroll.

**✍️ Self-review before you ask.** Authors run it locally and see the complexity they added *before* requesting review. Fewer "can you split this up?" round trips.

**🤝 Orientation, not gatekeeping.** PR Audit doesn't grade your code or block your merge. It gives everyone the same map of the change, so review conversations start from facts instead of first impressions.

**🔒 Safe to run anywhere.** No network access, no third-party dependencies, and it never executes the code under review. Python is parsed with the standard library's `ast`. Running it on a fork PR never runs the fork's code.

**♻️ Deterministic.** The same two refs always produce the same findings. No sampling, no LLM guesswork, no "it said something different this time".

---

## Get started in 30 seconds

**On your machine:**

```bash
pip install pr-audit
cd your-repo
pr-audit analyze
```

The base branch is inferred automatically. You get `audit.md` for humans and `audit.json` for tooling.

**On every pull request (GitHub Actions):**

```yaml
# .github/workflows/pr-audit.yml
name: PR Audit
on: pull_request
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

The audit lands in the job summary of every PR. Want it as a PR comment that updates itself, including on fork PRs? [It takes two files](#posting-the-audit-as-a-pr-comment).

---

## How it compares

| | **PR Audit** | radon / complexipy | Danger | CodeClimate / SonarQube |
|---|---|---|---|---|
| Scoped to one PR's diff | ✅ | ❌ whole files | ✅ | Partly |
| Before → after complexity per changed function | ✅ | ❌ | Write it yourself | Trends, not per-PR deltas |
| Ranked "read this first" list | ✅ | ❌ | ❌ | ❌ |
| Setup | One command, zero config | CLI | Write rules in JS/Ruby | Hosted service or server |
| Accounts, tokens, network | None | None | GitHub token | Required |
| Price | **Free forever** | Free | Free | Paid tiers |

PR Audit doesn't replace your linter, your tests, or your coverage tool. It answers the question those tools leave open: *"Where should I look first?"*

---

## Free forever, really

PR Audit is MIT licensed and runs entirely on your machine or your CI runner. There is no hosted backend to shut down, no usage cap, no telemetry, and no "community edition". The whole tool is what you see in this repo.

If it saves your team time, the best thanks is a ⭐ star, a bug report, or an idea in [Issues](https://github.com/cabusto/pr-audit/issues).

---

# Reference

## Install

```bash
python3 -m pip install pr-audit
```

Requires Python 3.12+. Currently analyzes Python repositories.

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

PR Audit ships as a composite action. The audit is written to the job summary and to `pr-audit-out/`. The checkout needs `fetch-depth: 0` so both refs are available.

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
- [`.github/workflows/pr-audit-comment.yml`](.github/workflows/pr-audit-comment.yml) runs after it, downloads the artifact, identifies the PR from trusted `workflow_run` metadata, and creates or updates a single bot comment.

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

````md
# PR Audit

## Scope
```text
+425 / -48 LOC
11 files changed · 2 added · 0 deleted

Production  8
Tests       3
Config      0
Docs        0
Dependency  0
Other       0
```

## Dependencies
```text
No dependency manifest changes detected
```

## Tests
```text
3 test files changed · 1 added
204 test LOC added
221 production LOC added
Production:test LOC ratio 1.1:1
```

## Structure
```text
Production files
1 added · 7 modified · 0 deleted

Python structure
3 classes added
9 functions/methods added
1 function/method removed
```

## Complexity
```text
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
```

## Review hotspots
```text
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
````

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

[MIT](LICENSE). Free to use, modify and ship, forever.

---

**Try it on your last PR.** It takes one command, and you'll know within a minute whether it earns a place in your workflow.

```bash
pip install pr-audit && pr-audit analyze
```
