# PR Audit — Sprint 1 Implementation Brief

Deterministic pull-request observability for Python repositories

> **Agent objective**
>
> Build a locally runnable Python CLI that compares two Git refs and produces a deterministic PR audit in both Markdown and JSON. The output should help a reviewer understand the structural shape of a change and decide where to start reviewing. Do not attempt to judge whether the code is “good” or “bad.”

Primary command

```text
pr-audit analyze --base main --head HEAD
```

This document is the build specification for Sprint 1. Treat the scope and non-goals as constraints unless an implementation detail is impossible or materially unsafe.

# 1. Product definition

PR Audit is a deterministic code-change analyzer. It does not replace code review. It summarizes measurable characteristics of a pull request and identifies files that deserve earlier reviewer attention.

## User problem

- Large or AI-generated PRs are expensive to orient around before substantive review can begin.

- Reviewers manually discover basic structural facts such as new dependencies, unusually large files, test changes, function growth, and increased nesting.

- Existing review tools often mix objective measurements with subjective AI judgments, which reduces trust.

## Sprint 1 outcome

Given a base ref and a head ref, the CLI must generate a concise audit containing:

- Scope metrics: lines and files changed.

- File classification: production, tests, config, docs, dependency manifests, and other.

- Python dependency changes from pyproject.toml and requirements.txt.

- Test-file changes and test-versus-production LOC.

- Changed Python functions with before/after LOC, cyclomatic complexity, and nesting depth.

- A deterministic, explainable review-hotspot ranking.

- Equivalent machine-readable JSON and human-readable Markdown outputs.

# 2. Hard scope and non-goals

> **Important**
>
> Keep Sprint 1 deliberately narrow. Do not introduce a plugin system, generic language framework, policy engine, LLM integration, GitHub App, database, web UI, or repository-wide semantic indexing.

## Supported in Sprint 1

- Python 3.12 runtime.

- Local Git repositories.

- Python source analysis.

- pyproject.toml and requirements.txt dependency manifests.

- CLI execution against any valid local Git refs.

## Explicitly deferred

- LLM-generated summaries or judgments.

- GitHub comments, Checks API, or hosted integrations.

- TypeScript/JavaScript AST analysis.

- Security/vulnerability scanning.

- Coverage calculation unless a future version ingests a coverage report.

- Configurable team policies or blocking thresholds.

- Claims such as “overengineered”, “unsafe”, or “bad architecture”.

# 3. CLI experience

## Required command

```text
pr-audit analyze --base <git-ref> --head <git-ref> [--format markdown|json|both] [--output <path>]
```

## Default behavior

- Default --head to HEAD if omitted.

- Require --base.

- Default --format to both.

- Write audit.json and audit.md into the current working directory unless --output is provided.

- Exit 0 when analysis completes, even if metrics are unusual. Metrics are informational, not policy failures.

- Exit non-zero for invalid refs, Git failures, parse failures that prevent a coherent audit, or filesystem errors.

```text
$ pr-audit analyze --base main --head HEAD
Analyzing main...HEAD
✓ 19 changed files
✓ dependencies analyzed
✓ Python functions analyzed
✓ audit.json
✓ audit.md
```

# 4. Required Markdown output

The Markdown should be concise enough to scan in a short scroll. Do not dump raw AST information or every unchanged function.

```text
# PR Audit

## Scope
+1,284 / -132 LOC
19 files changed · 4 added · 1 deleted

Production  10
Tests        6
Config       2
Docs         1

## Dependencies
Added
+ jsonschema
+ referencing

Updated
pydantic 2.8 -> 2.9

## Tests
6 test files changed · 3 added
412 test LOC added
872 production LOC added
Production:test LOC ratio 2.1:1

## Complexity
5 changed functions increased in complexity

routes_v2.post_guard
LOC         42 -> 127
Complexity   6 -> 18
Nesting      2 -> 5

## Review hotspots
HIGH  routes_v2.py
      +542 LOC · complexity +12 · max nesting +3

MED   validation.py
      +306 LOC · 2 dependencies introduced

LOW   test_helpers.py
      +184 LOC · test-only
```

# 5. Internal data model

Analysis must produce a stable internal model first. Markdown and JSON are renderers over that model. Do not let presentation logic leak into analyzers.

```text
Audit
├── metadata
│   ├── base_ref
│   ├── head_ref
│   └── generated_at
├── scope
│   ├── loc_added
│   ├── loc_deleted
│   ├── files_changed
│   ├── files_added
│   ├── files_deleted
│   └── categories
├── dependencies[]
├── tests
│   ├── files_changed
│   ├── files_added
│   ├── loc_added
│   ├── production_loc_added
│   └── production_test_ratio
├── files[]
│   ├── path
│   ├── status
│   ├── category
│   ├── loc_added
│   ├── loc_deleted
│   ├── functions[]
│   └── hotspot
└── summary
```

## Stable metric names

Expose or derive stable metric identifiers so future policy features can consume the same measurements without redesigning the audit model.

```text
pr.loc.added
pr.loc.deleted
pr.files.changed
pr.files.added
pr.files.deleted

dependency.runtime.added
dependency.runtime.removed
dependency.runtime.changed

tests.files.changed
tests.files.added
tests.loc.added

complexity.cyclomatic.max.before
complexity.cyclomatic.max.after
complexity.nesting.max.before
complexity.nesting.max.after
```

# 6. Suggested architecture

```text
src/pr_audit/
├── cli.py
├── models.py
├── git/
│   ├── diff.py
│   └── content.py
├── analyzers/
│   ├── scope.py
│   ├── dependencies.py
│   ├── tests.py
│   ├── functions.py
│   └── complexity.py
├── scoring/
│   └── hotspots.py
└── render/
    ├── json.py
    └── markdown.py

tests/
├── fixtures/
├── test_diff.py
├── test_dependencies.py
├── test_tests_analyzer.py
├── test_functions.py
├── test_complexity.py
├── test_hotspots.py
└── test_cli.py
```

## Dependency philosophy

- Prefer subprocess calls to the installed git binary over GitPython.

- Prefer Python standard-library ast for function and nesting analysis.

- Use a small, established cyclomatic-complexity library only if it materially reduces code and remains deterministic.

- Use Pydantic only if its validation benefit justifies the dependency; dataclasses are acceptable for the internal model.

- Do not introduce abstractions solely for hypothetical future language support.

# 7. Analyzer specifications

## 7.1 Git diff and scope

Use Git as the source of truth. Prefer commands whose output is stable and easy to parse.

```text
git diff --numstat <base>...<head>
git diff --name-status <base>...<head>
git show <ref>:<path>
```

- Count text-line additions and deletions from --numstat.

- Preserve file status: added, modified, deleted, renamed.

- Handle binary files without pretending they have text LOC.

- Renames should not be treated as delete + add when Git identifies a rename.

| Category | Initial deterministic rules |
| --- | --- |
| Tests | tests/**, test_*.py, *_test.py |
| Dependency | pyproject.toml, requirements*.txt |
| Docs | *.md, docs/** |
| Config | Common CI/tool config such as .github/**, *.toml, *.yaml, *.yml; dependency manifests take precedence |
| Production | Python source not classified above |
| Other | Everything else |

## 7.2 Dependency analyzer

- Compare manifest content at base and head refs; do not rely on the checked-out working-tree version alone.

- pyproject.toml: support standard PEP 621 project.dependencies plus common development/optional groups when straightforward to detect.

- requirements.txt: compare normalized package names and version/specifier text line-by-line after ignoring comments and blank lines.

- Report added, removed, and changed dependencies.

- Classify runtime vs development when the manifest makes that distinction explicit. Otherwise mark type as unknown rather than guessing.

> **Do not overreach**
>
> Do not resolve transitive dependency graphs, query package indexes, or perform vulnerability scanning in Sprint 1.

## 7.3 Test analyzer

- Use file classification to identify test files.

- Report test files changed and added.

- Report test LOC added/deleted separately from production LOC.

- For Python, optionally count added top-level or method functions whose names start with test_, but do not make this count the primary test metric.

- Never label these metrics as code coverage.

## 7.4 Changed-function analyzer

Analyze only changed Python files and report only functions affected by the diff. Use base and head versions of each file.

- Parse functions and async functions using ast.

- Record qualified names where practical, e.g. ClassName.method or module_function.

- Record start line, end line, and function LOC in base and head.

- Map changed diff line ranges to functions so unchanged functions are omitted.

- If a file fails to parse, record analysis as unavailable for that file and continue if the rest of the audit is coherent.

## 7.5 Complexity

- Function LOC: end_lineno - lineno + 1.

- Cyclomatic complexity: deterministic per-function measurement. If a library is used, pin the dependency and document its definition.

- Nesting depth: maximum nested depth of control-flow constructs inside the function.

Count the following constructs toward nesting depth:

- if / elif

- for / async for

- while

- try / except / finally

- with / async with

- match / case

> **Delta-first presentation**
>
> Prefer before -> after and delta measurements. A complexity value is more useful when the reviewer can see that a function moved from 6 to 18 than when they see “18” alone.

# 8. Review-hotspot scoring

The score is a reviewer-navigation heuristic, not a quality or risk verdict. Keep it simple, deterministic, and explainable.

```text
file_score =
    production_loc_changed
  + (sum_positive_cyclomatic_delta * 20)
  + (max_positive_nesting_delta * 30)
  + (runtime_dependencies_introduced_in_or_by_file * 50)
```

Implementation notes:

- For dependency manifests, attribute dependency-addition points to the manifest itself; do not infer usage locations in Sprint 1.

- Test-only files should not receive production-LOC points. They may still appear as LOW hotspots due to changed size.

- Sort descending by score, with changed LOC as the deterministic tie-breaker.

- Assign HIGH to the top 20% of scored files, MEDIUM to the next 30%, and LOW to the remainder. For very small PRs, ensure the top non-zero file can still be HIGH.

- Every displayed hotspot must include human-readable reasons derived directly from metrics.

```text
HIGH  routes_v2.py
      +542 LOC · cyclomatic complexity +12 · max nesting +3
```

# 9. Implementation tickets

| ID | Ticket | Deliverable | Acceptance criterion |
| --- | --- | --- | --- |
| S1-01 | Scaffold | Package, CLI entry point, test harness | pr-audit --help works; tests run locally. |
| S1-02 | Git diff parser | Changed files, statuses, +/- LOC | Matches git output on fixtures including rename/binary cases. |
| S1-03 | File classifier | Deterministic category per changed file | Fixture paths classify consistently. |
| S1-04 | Scope audit | Aggregate scope metrics | JSON contains correct aggregate counts. |
| S1-05 | Dependencies | pyproject.toml + requirements.txt diff | Added/removed/changed deps detected from refs. |
| S1-06 | Tests | Test-file and LOC metrics | Separates test and production LOC accurately. |
| S1-07 | Functions | Changed Python function mapping | Only functions intersecting changed lines are reported. |
| S1-08 | Complexity | LOC, cyclomatic, nesting before/after | Known fixture functions produce expected deltas. |
| S1-09 | Hotspots | Explainable deterministic ranking | Ranking is stable and every result has metric reasons. |
| S1-10 | JSON renderer | audit.json | Schema is stable and covered by snapshot/schema tests. |
| S1-11 | Markdown renderer | audit.md | Readable short-scroll output from same Audit model. |
| S1-12 | Dogfood | Run against historical PRs | At least 10 audits reviewed for correctness/usefulness. |

# 10. Recommended build order

```text
S1-01 -> S1-02 -> S1-03 -> S1-04
                         |        |
                         v        v
                       S1-05    S1-06
                         \        /
                          v      v
                           S1-07
                             |
                           S1-08
                             |
                           S1-09
                             |
                    S1-10 + S1-11
                             |
                           S1-12
```

Keep the CLI runnable after each ticket. Do not wait until the end to integrate the analyzers.

# 11. Testing strategy

## Unit fixtures

- Create tiny fixture repositories or temporary Git repositories inside tests.

- Commit a base state, mutate files, commit a head state, and run the actual Git commands through the analyzer.

- Include changes that add, delete, modify, and rename files.

- Include binary files and malformed Python files.

- Include pyproject.toml dependency add/remove/version-change cases.

- Include requirements.txt comments, blank lines, extras, and specifier changes.

- Include nested Python functions whose expected complexity and nesting values are known.

## Golden-output tests

- Snapshot representative audit.json outputs.

- Snapshot representative audit.md outputs.

- Normalize timestamps or other unstable metadata before snapshots.

- A metric change should require an intentional snapshot update.

# 12. Edge cases and failure behavior

| Case | Expected behavior |
| --- | --- |
| Invalid Git ref | Fail clearly with non-zero exit code and the invalid ref in the error. |
| No changes | Produce a valid empty audit; do not fail. |
| Binary file | Count as changed file; LOC is null/unavailable rather than zero if Git does not provide text counts. |
| Deleted Python file | Allow before metrics; after metrics are null. |
| Added Python file | Before metrics are null; after metrics are populated. |
| Python parse error | Mark function/complexity analysis unavailable for that file and continue when possible. |
| Dependency manifest parse error | Report analyzer error explicitly; do not silently omit dependency metrics. |
| Zero test LOC | Production:test ratio should be null/infinite-safe, never divide by zero. |
| Rename | Preserve rename status and analyze content under the head path. |

# 13. Sprint acceptance criteria

- Runs against a normal Python PR in under 30 seconds on a typical developer machine.

- LOC and file counts match Git.

- Dependency changes are correctly detected for supported manifests.

- Test and production LOC are separated correctly.

- Changed Python functions are mapped correctly.

- Function LOC, cyclomatic complexity, and nesting deltas are stable and covered by tests.

- Review hotspots are deterministic and explainable.

- audit.json and audit.md are generated from the same internal Audit model.

- A failure in one analyzable file does not necessarily destroy the entire audit; unavailable metrics are explicit.

- The Markdown output remains concise and reviewer-oriented.

# 14. Dogfood protocol

Before any GitHub integration, run the CLI against at least 10 historical PRs. Prefer PRs that generated significant review discussion or were unusually large.

1. Identify the merge-base/base commit and the PR head commit.

1. Run PR Audit against those refs.

1. Compare the audit with the issues reviewers actually discussed.

1. Record incorrect metrics, noisy hotspot rankings, and missing facts that would have helped orientation.

1. Change deterministic rules only when there is a repeatable reason, not to make one PR look better.

> **Primary validation question**
>
> Would this audit have helped a reviewer decide where to start before opening the diff?

# 15. Definition of done

Sprint 1 is done when the command below can be run against a real historical PR and the resulting Markdown is accurate enough that an engineer would choose to read it before beginning review:

```text
pr-audit analyze   --base <commit-before-pr>   --head <pr-head>   --format both
```

Do not add an LLM or GitHub integration to compensate for weaknesses in the deterministic audit. First make the measurements trustworthy and the output useful.

# 16. Implementation guardrails for the coding agent

- Prefer the simplest implementation that satisfies the acceptance criteria.

- Do not create extension points for requirements that are explicitly deferred.

- Do not add dependencies unless they remove substantial implementation complexity; document why each dependency is necessary.

- Keep modules cohesive and small enough to review, but do not split files merely to satisfy arbitrary size targets.

- Write tests alongside each analyzer rather than postponing them.

- Use deterministic outputs. Avoid environment-dependent ordering.

- When a measurement is ambiguous, expose the ambiguity or null value instead of guessing.

- Keep user-visible terminology factual: “review hotspot”, “complexity increased”, “dependency added”; avoid “bad”, “overengineered”, or “risky”.
