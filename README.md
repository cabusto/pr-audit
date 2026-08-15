# PR Audit

Deterministic pull-request audit for local Python repos.

It compares two Git refs and writes a stable audit in:

- `audit.json`
- `audit.md`

## Install

```bash
python3 -m pip install -e .
```

## Run

```bash
pr-audit analyze --base main --head HEAD
```

If you have not installed the console script yet, use:

```bash
python3 -m pr_audit analyze --base main --head HEAD
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

## What it reports

- Scope metrics
- File classification
- Dependency changes from `pyproject.toml` and `requirements.txt`
- Test vs production LOC
- Changed Python functions
- Cyclomatic complexity and nesting
- Deterministic review hotspots

