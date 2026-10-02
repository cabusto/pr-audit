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

## [0.1.0]

### Added
- `pr-audit analyze` CLI comparing two Git refs, writing `audit.json` and `audit.md`.
- Scope metrics and file classification (production, tests, config, docs, dependency, other).
- Dependency change detection for `pyproject.toml` and `requirements.txt`.
- Changed Python function detection with cyclomatic complexity and nesting depth.
- Structural metrics (classes and functions added or removed).
- Deterministic review hotspots.
- Base ref inference from the repository's default branch.
