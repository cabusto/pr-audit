# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- MIT license.
- Composite GitHub Action (`action.yml`) for running the audit in other repositories.
- CI workflow running the test suite on Python 3.12, 3.13 and 3.14.

### Changed
- Deleted production files count a quarter of their deleted lines toward the hotspot score and are never the "largest production change".
- CI workflow files (`.github/workflows/*.yml`) and `action.yml` now score as review hotspots.
- `LICENSE`, `COPYING`, `NOTICE`, `AUTHORS` and similar files classify as docs; `.gitignore`, `.editorconfig`, `*.cfg` and `*.ini` classify as config.
- Releases publish to PyPI with trusted publishing instead of an API token.
- The release workflow runs the test suite before publishing.
- Markdown report sections are fenced code blocks, so GitHub keeps their line breaks and column alignment.
- A shallow clone that is missing the base commit fails with a hint to fetch full history.

### Fixed
- Base-side file contents are read from the merge-base, matching the diff. Previously the audit failed when the base branch had deleted a changed file since the branch point, and function metrics compared against the wrong version otherwise.
- Files that can't be decoded no longer abort the audit. Only Python files and dependency manifests are read; Python files honour PEP 263 coding declarations; undecodable ones are reported as analysis errors.
- Submodule changes no longer abort the audit.
- Non-UTF-8 filenames no longer crash report writing.
- `pyproject.toml` values with the wrong type (for example `dependencies = "requests"`) are reported as dependency errors instead of producing bogus dependencies or a traceback.

### Security
- The PR comment workflow finds the target PR through the GitHub API instead of trusting a PR number from the analysis artifact, so a fork can no longer make the bot comment on other issues or PRs.
- The PR comment workflow rebuilds the comment from the uploaded report, keeping only plain section headings and putting everything else in code blocks, so a fork's report can't post links, images or @mentions.
- File paths in the markdown report can't break out of its code blocks.
- All workflow and action dependencies are pinned to commit SHAs and kept current by Dependabot.

## [0.1.0]

### Added
- `pr-audit analyze` CLI comparing two Git refs, writing `audit.json` and `audit.md`.
- Scope metrics and file classification (production, tests, config, docs, dependency, other).
- Dependency change detection for `pyproject.toml` and `requirements.txt`.
- Changed Python function detection with cyclomatic complexity and nesting depth.
- Structural metrics (classes and functions added or removed).
- Deterministic review hotspots.
- Base ref inference from the repository's default branch.
