# hnmcp v2: Full Rewrite

## TL;DR

> **Quick Summary**: Delete existing code, rebuild hnmcp from scratch around 3 primitives (Discover, Trust, Understand). Every result explains WHY it was chosen. Trust system uses EigenTrust to propagate from seed experts.
> 
> **Deliverables**:
> - New Python package `hnmcp/` with 6 modules (server, quality, cache, profiles, trust, embeddings)
> - Full TDD test suite (90%+ coverage)
> - Rewritten README with philosophy section
> - Updated pyproject.toml with optional deps
> 
> **Estimated Effort**: Large (5-7 days)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Scaffold → Cache → Quality → Trust → Server → README

---

## Context

### Original Request
User wants to rebuild hnmcp from scratch. Existing 451-line single-file implementation is discarded. The tool's essence: HN has engineering knowledge buried in comments by practitioners. hnmcp helps find it through the user's lens, prioritizing trusted experts' content and explaining WHY every result matters.

### Interview Summary
**Key Decisions**:
- Delete all existing code, start fresh
- 3 primitives: Discover (find relevant content), Trust (know who's talking), Understand (explain why)
- Trust is central: go-to person's content gets prioritized
- Learning curve must be lean: easy to start, deep to customize
- Embeddings as optional dependency (`pip install hnmcp[embeddings]`)
- JSON profiles (`~/.hnmcp/profile.json`) + env var fallback
- Module split: server.py, quality.py, cache.py, profiles.py, trust.py, embeddings.py
- TDD with full test coverage

**Research Findings**:
- HN Algolia API supports `author + keyword` search (e.g., `query=security&tags=comment,author_tptacek` → 4620 hits)
- EigenTrust (Stanford 2003): proven trust propagation from seed nodes via reply graph
- Dynamic weighting: unknown authors 60/40 content/trust, proven experts 20/80
- Wilson Score CANNOT be used — HN only exposes net score, not success/total pair
- Practitioner markers validated: "I built", "FWIW", "YMMV", code blocks, specific metrics
- HN 65% negative sentiment but 27% more engagement — don't penalize negativity
- Algolia has no comment points — comment quality must use signal-based scoring only

### Metis Review
**Critical Gaps Addressed**:
- Wilson Score replaced with log-normalized scoring (stories) + signal-based scoring (comments)
- Trust algorithms locked to EigenTrust only (co-citation, Louvain deferred to v2)
- Dynamic weighting simplified to binary (seed expert vs non-expert) for v1
- Quality weights fixed at 5 signals — no user-customizable weights in v1
- Module dependency graph enforced: no circular imports
- FastMCP version validation required before implementation
- Trust graph persistence: cache to `~/.hnmcp/trust_cache.json` (survives restarts)
- `signals` dict schema defined upfront — all tools must include it

---

## Work Objectives

### Core Objective
Rebuild hnmcp as a modular Python package that surfaces HN content through the user's personal lens, with trust-based expert prioritization and full explainability.

### Concrete Deliverables
- `hnmcp/` Python package with 6 modules + `__init__.py` + `__main__.py`
- `tests/` with 7 test files + conftest.py (90%+ coverage)
- Updated `README.md` with philosophy, 3-primitives architecture, setup guide
- Updated `pyproject.toml` with new deps and entry points
- Updated `examples/` with new config format

### Definition of Done
- [ ] `pip install -e .` succeeds
- [ ] `python -m hnmcp` starts server
- [ ] `pytest --cov=hnmcp --cov-fail-under=90` passes
- [ ] All 5 quality signals implemented and tested
- [ ] EigenTrust propagates trust from seed experts (verified with mock graph)
- [ ] Every tool response includes `signals` dict with reasoning
- [ ] `pip install -e ".[embeddings]"` installs optional deps
- [ ] Profile loading: JSON file → env var fallback → defaults (all paths tested)
- [ ] Error handling: API failures return structured error messages

### Must Have
- 3 primitives (Discover, Trust, Understand) as concrete MCP tools
- `signals` dict on every response explaining WHY
- EigenTrust trust propagation from seed experts
- 5-signal quality scoring (Practitioner, Velocity, Reference, Thread Depth, Expert)
- TTL caching with async-safe access
- JSON profile support with env var fallback
- Error handling with structured messages for AI agents
- Full TDD test suite

### Must NOT Have (Guardrails)
- No co-citation, Louvain, or bibliographic coupling algorithms (v2)
- No user-customizable quality weights (v2)
- No persistent vector database for embeddings (session-only)
- No web UI
- No Redis or external cache dependency
- No `X | Y` union syntax (Python 3.9 compat — use `Optional[X]`)
- No expanding practitioner markers beyond validated 8
- No live HN API calls in tests
- No Wilson Score (inapplicable to HN data)
- Do NOT penalize negative sentiment in quality scoring

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio in pyproject.toml)
- **Automated tests**: TDD (tests written BEFORE implementation)
- **Framework**: pytest + pytest-asyncio + respx + time-machine
- **Coverage target**: 90%+

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/`.

- **Modules**: Use Bash (pytest) — run tests, assert pass/fail
- **Server integration**: Use Bash (python -m hnmcp + curl/MCP client) — start server, call tools, verify responses
- **README**: Use Read tool — verify all sections present, no broken links

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — start immediately):
├── Task 1: Project scaffold + delete old code [quick]
├── Task 2: Test infrastructure + shared fixtures [quick]
├── Task 3: README philosophy rewrite [writing]
└── Task 4: pyproject.toml + packaging update [quick]

Wave 2 (Core modules — independent, MAX PARALLEL):
├── Task 5: Cache module (TDD) [deep]
├── Task 6: Profiles module (TDD) [deep]
└── Task 7: Quality scoring module (TDD) [deep]

Wave 3 (Dependent modules):
├── Task 8: Trust module — EigenTrust (TDD) (depends: 5) [deep]
├── Task 9: Embeddings module (TDD) (depends: 5) [deep]
└── Task 10: MCP Server — tools + lifespan (depends: 5,6,7,8) [deep]

Wave 4 (Integration + verification):
├── Task 11: Integration tests (depends: 10) [deep]
├── Task 12: Examples + config migration docs (depends: 10) [quick]
└── Task 13: Final QA + coverage (depends: 11) [unspecified-high]

Wave FINAL (Independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 5 → Task 8 → Task 10 → Task 11 → Task 13 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 (scaffold) | — | 2,3,4,5,6,7 |
| 2 (test infra) | 1 | 5,6,7,8,9 |
| 3 (README) | 1 | 12 |
| 4 (pyproject) | 1 | 10 |
| 5 (cache) | 1,2 | 8,9,10 |
| 6 (profiles) | 1,2 | 10 |
| 7 (quality) | 1,2 | 10 |
| 8 (trust) | 5 | 10 |
| 9 (embeddings) | 5 | 10 |
| 10 (server) | 5,6,7,8 | 11 |
| 11 (integration) | 10 | 13 |
| 12 (examples) | 10 | F1-F4 |
| 13 (final QA) | 11 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: 4 tasks — T1,T2,T4 → `quick`, T3 → `writing`
- **Wave 2**: 3 tasks — T5,T6,T7 → `deep`
- **Wave 3**: 3 tasks — T8,T9 → `deep`, T10 → `deep`
- **Wave 4**: 3 tasks — T11 → `deep`, T12 → `quick`, T13 → `unspecified-high`
- **FINAL**: 4 tasks — F1 → `oracle`, F2,F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Project Scaffold + Delete Old Code

  **What to do**:
  - Delete `hnmcp.py` (old single-file implementation)
  - Create package structure:
    ```
    hnmcp/
    ├── __init__.py          # Package entry, version, FastMCP app export
    ├── __main__.py          # python -m hnmcp entry point
    ├── server.py            # MCP tools + lifespan (empty stub)
    ├── quality.py           # Quality scoring (empty stub)
    ├── cache.py             # TTL cache (empty stub)
    ├── profiles.py          # Profile loading (empty stub)
    ├── trust.py             # EigenTrust (empty stub)
    └── embeddings.py        # Optional embeddings (empty stub)
    ```
  - Validate FastMCP version supports `@lifespan` + `Context.lifespan_context` — run minimal test:
    ```python
    from fastmcp import FastMCP, Context
    mcp = FastMCP("test")
    # Verify lifespan decorator exists
    ```
  - If FastMCP version too old, update `pyproject.toml` to pin correct minimum version

  **Must NOT do**:
  - Don't implement any logic yet — stubs only
  - Don't use `X | Y` type syntax

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 2, 3, 4, 5, 6, 7
  - **Blocked By**: None

  **References**:
  - `hnmcp.py` — DELETE this file entirely
  - FastMCP docs: https://gofastmcp.com — check lifespan API
  - `pyproject.toml` — update entry point from `hnmcp:mcp.run` to `hnmcp.server:mcp.run`

  **Acceptance Criteria**:
  - [ ] `hnmcp.py` no longer exists
  - [ ] `hnmcp/__init__.py` exists and is importable
  - [ ] `python -c "from fastmcp import FastMCP, Context; print('OK')"` succeeds
  - [ ] All 6 module stubs exist as empty files with module docstrings

  **QA Scenarios**:
  ```
  Scenario: Package is importable after scaffold
    Tool: Bash
    Steps:
      1. Run `python -c "import hnmcp; print(hnmcp.__version__)"`
      2. Assert exit code 0
      3. Assert output contains version string (e.g., "0.2.0")
    Expected Result: Import succeeds, version printed
    Evidence: .sisyphus/evidence/task-1-import.txt

  Scenario: Old file is deleted
    Tool: Bash
    Steps:
      1. Run `test -f hnmcp.py && echo "EXISTS" || echo "DELETED"`
      2. Assert output is "DELETED"
    Expected Result: hnmcp.py does not exist
    Evidence: .sisyphus/evidence/task-1-deleted.txt
  ```

  **Commit**: YES
  - Message: `scaffold: project structure, delete old single-file implementation`
  - Files: `hnmcp/__init__.py`, `hnmcp/__main__.py`, `hnmcp/server.py`, `hnmcp/quality.py`, `hnmcp/cache.py`, `hnmcp/profiles.py`, `hnmcp/trust.py`, `hnmcp/embeddings.py`
  - Removed: `hnmcp.py`

- [x] 2. Test Infrastructure + Shared Fixtures

  **What to do**:
  - Create `tests/` directory structure:
    ```
    tests/
    ├── __init__.py
    ├── conftest.py            # Shared fixtures
    ├── test_cache.py          # (empty, created in Task 5)
    ├── test_profiles.py       # (empty, created in Task 6)
    ├── test_quality.py        # (empty, created in Task 7)
    ├── test_trust.py          # (empty, created in Task 8)
    ├── test_embeddings.py     # (empty, created in Task 9)
    └── test_server.py         # (empty, created in Task 10)
    ```
  - `conftest.py` must contain shared fixtures:
    - `mock_story`: Sample HN story dict with all fields (id, title, score, by, descendants, time, kids, url, text)
    - `mock_comment`: Sample HN comment dict (id, by, text, time, kids, parent, deleted=False)
    - `mock_expert_comment`: Comment with practitioner markers ("I built", code block)
    - `mock_user_profile`: Firebase user dict (id, karma, created, about, submitted)
    - `mock_algolia_response`: Algolia search response with hits array
    - `sample_profile_json`: Valid profile.json content
    - `sample_trust_graph`: Small trust matrix (5 users) with hand-calculated EigenTrust scores
    - `tmp_profile_dir`: Temp directory fixture for profile file tests
  - Define `signals` schema as a shared constant or fixture:
    ```python
    SIGNALS_SCHEMA = {
        "practitioner_depth": {"score": float, "markers": list},
        "velocity": {"score": float, "points_per_hour": float},
        "reference_density": {"score": float, "link_count": int},
        "thread_depth": {"score": float, "max_depth": int},
        "expert_involvement": {"score": float, "experts": list, "trust_scores": dict}
    }
    ```

  **Must NOT do**:
  - Don't write actual tests yet — only fixtures and helpers
  - Don't create tests that hit live HN APIs

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Tasks 5, 6, 7, 8, 9
  - **Blocked By**: Task 1

  **References**:
  - HN Firebase API response shapes (from explore agent research):
    - Story: `{id, title, score, by, descendants, time, kids, url, text, type}`
    - Comment: `{id, by, text, time, kids, parent, type, deleted, dead}`
    - User: `{id, karma, created, about, submitted}`
  - HN Algolia API response shape: `{hits: [{author, comment_text, created_at_i, objectID, parent_id, story_id, story_title, points, children}], nbHits, nbPages}`
  - EigenTrust hand-calculated example: 5 users, seed=[A,B], reply edges A→C, B→C, C→D, D→E → expected trust order: A=B > C > D > E

  **Acceptance Criteria**:
  - [ ] `pytest --collect-only` shows all test files discovered
  - [ ] `conftest.py` defines all 8 fixtures listed above
  - [ ] `SIGNALS_SCHEMA` constant exported and importable
  - [ ] Fixtures produce valid data structures (each fixture returns non-None)

  **QA Scenarios**:
  ```
  Scenario: Fixtures are collectible
    Tool: Bash
    Steps:
      1. Run `pytest --collect-only tests/conftest.py`
      2. Assert exit code 0
      3. Assert output contains "mock_story", "mock_comment", "sample_trust_graph"
    Expected Result: All fixtures visible
    Evidence: .sisyphus/evidence/task-2-fixtures.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `test: add test infrastructure with shared fixtures and signal schema`
  - Files: `tests/__init__.py`, `tests/conftest.py`

- [x] 3. README Philosophy Rewrite

  **What to do**:
  - Replace entire README content with new version centered on 3 primitives
  - **"Why" section** (use exact text from draft — verified and approved by user):
    ```
    ## Why

    HN is where engineers share lessons that cost them months to learn — in a
    single comment. tptacek has 4,600+ comments on security. patio11 has written
    more about SaaS pricing on HN than most books cover. The best engineering
    knowledge isn't in the stories that get upvoted to the front page. It's
    buried in comment threads, written by people who've actually built the thing.

    The problem is finding it. HN's ranking shows you what's popular, not what's
    relevant to you. And more importantly — it doesn't tell you who to listen to.
    On any thread about databases, there might be 200 comments. Three of them are
    from people who've run Postgres at scale. The rest are opinions. Knowing which
    three — that's the difference between learning something real and wasting
    twenty minutes.

    hnmcp does three things:

    1. **Discover** — Find content that matters to you, not what's trending. Your
       keywords, your score thresholds, your time window.

    2. **Trust** — Know who's talking. hnmcp tracks domain experts, detects
       practitioner signals ("I built this", "we ran this in production", code
       blocks, specific metrics), and tells you *why* a comment is worth reading.
       When you follow experts, their network becomes visible too — people they
       engage with are probably worth listening to.

    3. **Understand** — Every result comes with its reasoning. Not just a score,
       but the signals behind it: practitioner depth, score velocity, reference
       density, thread depth, expert involvement. You see why the filter chose
       what it chose. If it's wrong, you adjust.

    **Why AI-native?** Because this isn't a feed to scroll. It's a knowledge base
    to query. You ask your AI agent "what did practitioners say about Kubernetes
    networking this week?" and get a structured answer with sources and trust
    signals — not a list of links.
    ```
  - Keep sections: Quick Start, Available Tools (update to new tools), Quality Signals, Environment Variables, Examples (update), Architecture (update), License, Contributing
  - Remove: old Features bullet list, old Roadmap section, Recommended Experts (move to examples/), Credits
  - Add migration note: "If upgrading from v1, update your Claude Desktop config path"

  **Must NOT do**:
  - No emoji in headers (keep it clean and professional)
  - No marketing language ("best-in-class", "seamless", "powerful")
  - No placeholder text — every section must have real content

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 12
  - **Blocked By**: Task 1

  **References**:
  - Draft philosophy text: `.sisyphus/drafts/full-implementation.md` → "README Philosophy" section
  - Current README structure: `README.md` — preserve Quick Start, Configuration, License sections
  - Librarian research on philosophy patterns: Reader.dev "I got tired of..." pattern, Current RSS "what I left out" pattern

  **Acceptance Criteria**:
  - [ ] "Why" section contains exact text from draft (3 primitives: Discover, Trust, Understand)
  - [ ] No emoji in section headers
  - [ ] No "Roadmap" section (removed)
  - [ ] Migration note present for v1 users
  - [ ] Quick Start section updated with `python -m hnmcp` entry point

  **QA Scenarios**:
  ```
  Scenario: Philosophy section is present and correct
    Tool: Bash (grep)
    Steps:
      1. grep "tptacek has 4,600" README.md
      2. grep "Discover.*Trust.*Understand" README.md
      3. grep -c "🎯\|🧠\|👥\|🔍\|📊\|⚡" README.md (should be 0 — no emoji headers)
    Expected Result: Philosophy text found, no emoji headers
    Evidence: .sisyphus/evidence/task-3-readme.txt
  ```

  **Commit**: YES
  - Message: `docs: rewrite README with philosophy and 3-primitives architecture`
  - Files: `README.md`

- [x] 4. pyproject.toml Update

  **What to do**:
  - Update dependencies:
    ```toml
    dependencies = [
        "fastmcp>=2.0.0",
        "httpx>=0.24.0",
    ]

    [project.optional-dependencies]
    embeddings = [
        "sentence-transformers>=2.0.0",
    ]
    dev = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.0.0",
        "respx>=0.20.0",
        "time-machine>=2.0.0",
        "black>=23.0.0",
        "ruff>=0.1.0",
    ]
    ```
  - Update entry point: `hnmcp = "hnmcp.server:main"`
  - Update version to `0.2.0`
  - Replace placeholder author/URL with real values (ask user or leave generic)
  - Add `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`

  **Must NOT do**:
  - Don't add numpy as required dep (EigenTrust will use pure Python)
  - Don't add cachetools (manual TTL cache)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 10
  - **Blocked By**: Task 1

  **References**:
  - Current `pyproject.toml` — preserve classifiers, tool configs
  - FastMCP version: verify minimum version that supports lifespan (likely >=2.0.0)

  **Acceptance Criteria**:
  - [ ] `pip install -e ".[dev]"` succeeds
  - [ ] `pip install -e ".[embeddings]"` succeeds (if torch available)
  - [ ] `pip install -e .` does NOT install sentence-transformers
  - [ ] Version is `0.2.0`

  **QA Scenarios**:
  ```
  Scenario: Dev install succeeds
    Tool: Bash
    Steps:
      1. Run `pip install -e ".[dev]"`
      2. Assert exit code 0
      3. Run `python -c "import respx; import time_machine; print('OK')"`
      4. Assert output "OK"
    Expected Result: All dev deps installed
    Evidence: .sisyphus/evidence/task-4-install.txt
  ```

  **Commit**: YES
  - Message: `chore: update pyproject.toml with new deps and module entry point`
  - Files: `pyproject.toml`

---

- [x] 5. Cache Module (TDD)

  **What to do**:
  - **Write tests FIRST** in `tests/test_cache.py`:
    - `test_cache_set_get`: Set value, get returns it
    - `test_cache_ttl_expiry`: Set with TTL, time-travel past TTL, get returns None
    - `test_cache_different_ttls`: Story (5min), item (10min), user (30min) TTLs
    - `test_cache_async_safe`: Concurrent access doesn't corrupt
    - `test_cache_clear`: Clear removes all entries
    - `test_cache_stampede_protection`: Two concurrent misses → only one fetch (asyncio.Lock)
  - **Then implement** `hnmcp/cache.py`:
    - `TTLCache` class with:
      - `async get(key: str) -> Optional[Any]`
      - `async set(key: str, value: Any, ttl: int) -> None`
      - `async get_or_fetch(key: str, fetcher: Callable, ttl: int) -> Any` (with lock)
      - `clear() -> None`
    - Default TTLs as constants: `STORY_TTL = 300`, `ITEM_TTL = 600`, `USER_TTL = 1800`
    - Use `asyncio.Lock` per-key for stampede protection
    - Pure Python — no external deps (dict + timestamp)

  **Must NOT do**:
  - No Redis, no cachetools, no external cache library
  - No LRU eviction (simple TTL only for v1)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7)
  - **Blocks**: Tasks 8, 9, 10
  - **Blocked By**: Tasks 1, 2

  **References**:
  - `time-machine` docs: `@time_machine.travel()` + `traveller.shift(timedelta(seconds=301))`
  - `asyncio.Lock` pattern for stampede protection

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_cache.py` — all tests pass
  - [ ] TTL expiry verified with time-machine (not real sleep)
  - [ ] Stampede protection verified (only 1 fetch for N concurrent misses)

  **QA Scenarios**:
  ```
  Scenario: Cache TTL expires correctly
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_cache.py::test_cache_ttl_expiry -v`
      2. Assert PASSED
    Expected Result: Cache returns None after TTL expires (via time-machine)
    Evidence: .sisyphus/evidence/task-5-ttl.txt

  Scenario: Stampede protection works
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_cache.py::test_cache_stampede_protection -v`
      2. Assert PASSED
    Expected Result: Only 1 fetcher call despite multiple concurrent gets
    Evidence: .sisyphus/evidence/task-5-stampede.txt
  ```

  **Commit**: YES
  - Message: `feat(cache): TTL cache with async-safe access and stampede protection`
  - Files: `hnmcp/cache.py`, `tests/test_cache.py`
  - Pre-commit: `pytest tests/test_cache.py`

- [x] 6. Profiles Module (TDD)

  **What to do**:
  - **Write tests FIRST** in `tests/test_profiles.py`:
    - `test_load_from_json`: Valid `~/.hnmcp/profile.json` → loads all fields
    - `test_load_fallback_env`: No JSON file → falls back to env vars
    - `test_load_fallback_defaults`: No JSON, no env → uses defaults
    - `test_malformed_json`: Invalid JSON → warning logged, falls back to env
    - `test_env_overrides_defaults`: `HN_KEYWORDS="ai,rust"` → keywords=["ai","rust"]
    - `test_empty_string_env`: `HN_KEYWORDS=""` → empty list (NOT `[""]`)
    - `test_profile_schema_validation`: Extra/missing fields handled gracefully
    - `test_profile_reload`: Profile file changes → next call picks up new values (no caching)
  - **Then implement** `hnmcp/profiles.py`:
    - `Profile` dataclass:
      ```python
      @dataclass
      class Profile:
          keywords: List[str] = field(default_factory=list)
          experts: List[str] = field(default_factory=list)
          min_score: int = 0
          time_hours: int = 24
          weights: Dict[str, float] = field(default_factory=lambda: {
              "practitioner": 0.30,
              "velocity": 0.15,
              "reference": 0.15,
              "thread_depth": 0.20,
              "expert": 0.20,
          })
      ```
    - `load_profile(path: Optional[str] = None) -> Profile`:
      1. Try `path` or `~/.hnmcp/profile.json`
      2. Fall back to env vars (`HN_KEYWORDS`, `HN_MIN_SCORE`, `HN_EXPERTS`, `HN_TIME_HOURS`)
      3. Fall back to defaults
    - Handle empty strings: `"".split(",")` → `[]` not `[""]`
    - Log warning on malformed JSON (don't crash)

  **Must NOT do**:
  - No quality weight customization in profile for v1 (weights are fixed)
    - CORRECTION from Metis: actually the user approved weights in profile during interview. Include `weights` field in profile schema but keep defaults sensible.
  - No pydantic dependency for validation (use manual checks)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 1, 2

  **References**:
  - Draft profile schema from interview:
    ```json
    {
      "keywords": ["ai", "distributed systems"],
      "experts": ["simonw", "tptacek"],
      "min_score": 30,
      "weights": {"practitioner": 0.3, "velocity": 0.1, "reference": 0.1, "thread_depth": 0.2, "expert": 0.3}
    }
    ```
  - Environment variable names: `HN_KEYWORDS`, `HN_MIN_SCORE`, `HN_EXPERTS`, `HN_TIME_HOURS`

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_profiles.py` — all tests pass
  - [ ] JSON → env → defaults fallback chain verified
  - [ ] Empty string env vars produce empty lists
  - [ ] Malformed JSON logs warning, doesn't crash

  **QA Scenarios**:
  ```
  Scenario: Profile fallback chain
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_profiles.py -v`
      2. Assert all 8 tests PASSED
    Expected Result: All fallback scenarios covered
    Evidence: .sisyphus/evidence/task-6-profiles.txt

  Scenario: Malformed JSON doesn't crash
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_profiles.py::test_malformed_json -v`
      2. Assert PASSED
    Expected Result: Warning logged, env var fallback used
    Evidence: .sisyphus/evidence/task-6-malformed.txt
  ```

  **Commit**: YES
  - Message: `feat(profiles): profile loading with JSON, env var fallback, and defaults`
  - Files: `hnmcp/profiles.py`, `tests/test_profiles.py`
  - Pre-commit: `pytest tests/test_profiles.py`

- [x] 7. Quality Scoring Module (TDD)

  **What to do**:
  - **Write tests FIRST** in `tests/test_quality.py`:
    - `test_practitioner_markers_detected`: Comment with "I built" → `practitioner_depth.score > 0`
    - `test_practitioner_markers_with_code_block`: `<pre>` tag → detected
    - `test_velocity_scoring`: Story with 50pts in 1hr → high velocity
    - `test_velocity_old_story`: 5-year-old story → near-zero velocity (with floor)
    - `test_reference_density`: Comment with 3 URLs → `reference_density.score > 0`
    - `test_thread_depth`: Comment tree 4 levels deep → high thread_depth score
    - `test_expert_involvement`: Seed expert commented → `expert_involvement.score > 0`
    - `test_full_signals_schema`: Output matches `SIGNALS_SCHEMA` from conftest
    - `test_story_quality_score`: Full story scoring (log-normalized, NOT Wilson)
    - `test_comment_quality_score`: Comment scoring (signal-based only, no points)
    - `test_negative_sentiment_not_penalized`: Negative comment tone → no score reduction
    - `test_score_range`: All scores normalized 0.0-1.0
  - **Then implement** `hnmcp/quality.py`:
    - `PRACTITIONER_MARKERS = ["i built", "we used", "in production", "our team", "i tried", "we deployed", "at scale", "my experience"]`
    - `HEDGING_MARKERS = ["fwiw", "ymmv", "imho", "in my opinion", "depends on"]`
    - `calculate_signals(item: dict, context: dict) -> dict`: Returns full signals breakdown
    - `calculate_quality_score(signals: dict, weights: dict) -> float`: Weighted sum
    - `detect_practitioner_markers(text: str) -> List[str]`: Returns matched markers
    - `count_references(text: str) -> int`: Count http/https links
    - `calculate_velocity(score: int, age_seconds: int) -> float`: Points per hour, min age floor
    - For stories: log-normalized score + velocity + reference + thread depth + expert
    - For comments: practitioner markers + reference + hedging + expert (NO points-based scoring)
    - All functions return `signals` dict matching `SIGNALS_SCHEMA`

  **Must NOT do**:
  - No Wilson Score (HN doesn't provide success/total)
  - No sentiment analysis (don't penalize negativity)
  - Don't expand markers beyond the 8 validated ones
  - Don't add ML-based detection

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 1, 2

  **References**:
  - Existing markers list from old `hnmcp.py:80-89` and `hnmcp.py:121-129` (preserve these exact strings)
  - Expert detection regex from old `hnmcp.py:134`: `r"\d+%|\d+x|\$\d+|v\d+\.\d+"`
  - Sift.1mb.dev practitioner depth scoring (30% practitioner, 15% velocity, 15% reference, 20% thread depth, 20% expert)
  - HN sentiment research: 65% negative, 27% more engagement — negativity is signal, not noise

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_quality.py` — all 12 tests pass
  - [ ] Every output includes full `signals` dict
  - [ ] Score range 0.0-1.0 for all values
  - [ ] Practitioner markers return matched strings (not just bool)
  - [ ] No sentiment penalty

  **QA Scenarios**:
  ```
  Scenario: Practitioner comment gets high score
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_quality.py::test_practitioner_markers_detected -v`
      2. Assert PASSED
    Expected Result: "I built" marker detected, practitioner_depth.score > 0
    Evidence: .sisyphus/evidence/task-7-practitioner.txt

  Scenario: Signals schema is correct
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_quality.py::test_full_signals_schema -v`
      2. Assert PASSED
    Expected Result: Output has all 5 signal keys with correct sub-fields
    Evidence: .sisyphus/evidence/task-7-schema.txt
  ```

  **Commit**: YES
  - Message: `feat(quality): 5-signal quality scoring with explainability`
  - Files: `hnmcp/quality.py`, `tests/test_quality.py`
  - Pre-commit: `pytest tests/test_quality.py`

---

- [x] 8. Trust Module — EigenTrust (TDD)

  **What to do**:
  - **Write tests FIRST** in `tests/test_trust.py`:
    - `test_eigentrust_basic`: 5-user mock graph → trust scores match hand-calculated values
    - `test_eigentrust_seed_highest`: Seed experts always have highest trust
    - `test_eigentrust_propagation`: User who replies to seed expert gets elevated trust
    - `test_eigentrust_single_seed`: Works with only 1 seed expert
    - `test_eigentrust_no_interactions`: No reply data → all trust = pre-trust values
    - `test_eigentrust_convergence`: Converges within 50 iterations
    - `test_eigentrust_max_users_cap`: Graph with >500 users → capped to 500
    - `test_trust_cache_persistence`: Trust data saves to `~/.hnmcp/trust_cache.json`
    - `test_trust_cache_load`: Persisted trust data loads on restart
    - `test_is_trusted_expert`: Binary check: seed expert → True, high-trust → True, low-trust → False
  - **Then implement** `hnmcp/trust.py`:
    - `build_reply_graph(comments: List[dict]) -> Dict[str, Dict[str, int]]`: Count reply interactions
    - `compute_eigentrust(reply_graph, seed_experts, alpha=0.15, max_iter=50, epsilon=1e-4) -> Dict[str, float]`: Pure Python implementation (no numpy)
    - `is_trusted(username: str, trust_scores: dict, threshold: float = 0.3) -> bool`
    - `get_trust_score(username: str, trust_scores: dict) -> float`
    - `save_trust_cache(trust_scores: dict, path: str) -> None`
    - `load_trust_cache(path: str) -> Optional[Dict[str, float]]`
    - Constants: `MAX_TRUST_USERS = 500`, `TRUST_ALPHA = 0.15`, `MAX_ITERATIONS = 50`
    - Uses `hnmcp/cache.py` for in-memory caching of trust computations

  **Must NOT do**:
  - No numpy (pure Python matrix operations — list of lists)
  - No co-citation, Louvain, or bibliographic coupling (v2)
  - No continuous trust learning — binary seed/non-seed for dynamic weighting
  - No graph larger than 500 users

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 9)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 10
  - **Blocked By**: Task 5 (needs cache)

  **References**:
  - EigenTrust paper formula: `t_i = (1-a) * Σ(c_ij * t_j) + a * p_i` where a=0.15
  - Hand-calculated test case from conftest: `sample_trust_graph` fixture
  - Trust cache path: `~/.hnmcp/trust_cache.json`

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_trust.py` — all 10 tests pass
  - [ ] EigenTrust converges on mock graph with correct ranking
  - [ ] Pure Python — no numpy import
  - [ ] Trust cache persists and loads correctly
  - [ ] Max 500 users enforced

  **QA Scenarios**:
  ```
  Scenario: EigenTrust produces correct trust order
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_trust.py::test_eigentrust_basic -v`
      2. Assert PASSED
    Expected Result: trust(seed) > trust(replied_to_seed) > trust(random)
    Evidence: .sisyphus/evidence/task-8-eigentrust.txt

  Scenario: Trust persists across restarts
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_trust.py::test_trust_cache_persistence -v`
      2. Run `pytest tests/test_trust.py::test_trust_cache_load -v`
      3. Assert both PASSED
    Expected Result: Save → load roundtrip preserves trust scores
    Evidence: .sisyphus/evidence/task-8-persistence.txt
  ```

  **Commit**: YES
  - Message: `feat(trust): EigenTrust with seed expert propagation and persistence`
  - Files: `hnmcp/trust.py`, `tests/test_trust.py`
  - Pre-commit: `pytest tests/test_trust.py`

- [x] 9. Embeddings Module (TDD)

  **What to do**:
  - **Write tests FIRST** in `tests/test_embeddings.py`:
    - `test_import_without_deps`: `import hnmcp.embeddings` doesn't crash without sentence-transformers
    - `test_embed_text`: Text → vector (with mocked model)
    - `test_find_similar`: Given embedded stories, find most similar to query
    - `test_session_only`: Embeddings don't persist between calls (no file storage)
    - `test_graceful_degradation`: When sentence-transformers not installed, functions return helpful error
  - **Then implement** `hnmcp/embeddings.py`:
    - Lazy import: `sentence_transformers` imported only when first called
    - `EmbeddingStore` class (session-scoped):
      - `add(item_id: str, text: str) -> None`
      - `find_similar(query: str, top_k: int = 5) -> List[Tuple[str, float]]`
      - `clear() -> None`
    - If sentence-transformers not installed → raise `ImportError` with message: "Install with: pip install hnmcp[embeddings]"
    - Uses `hnmcp/cache.py` for caching embeddings within session

  **Must NOT do**:
  - No persistent vector DB
  - No automatic model download on import (only when first used)
  - No clustering or topic modeling
  - Don't make any other module depend on this

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 8)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 10
  - **Blocked By**: Task 5 (needs cache)

  **References**:
  - `pytest.importorskip("sentence_transformers")` for tests requiring the dep
  - `pyproject.toml` optional deps: `[project.optional-dependencies] embeddings = ["sentence-transformers>=2.0.0"]`

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_embeddings.py` — all pass (even without sentence-transformers installed)
  - [ ] Import doesn't crash without optional dep
  - [ ] Helpful error message when dep missing
  - [ ] Session-only storage (no files created)

  **QA Scenarios**:
  ```
  Scenario: Graceful without optional deps
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_embeddings.py::test_graceful_degradation -v`
      2. Assert PASSED
    Expected Result: Clear error message, no crash
    Evidence: .sisyphus/evidence/task-9-graceful.txt
  ```

  **Commit**: YES
  - Message: `feat(embeddings): optional semantic similarity search`
  - Files: `hnmcp/embeddings.py`, `tests/test_embeddings.py`
  - Pre-commit: `pytest tests/test_embeddings.py`

- [ ] 10. MCP Server — Tools + Lifespan

  **What to do**:
  - **Write tests FIRST** in `tests/test_server.py`:
    - `test_discover_top_stories`: Returns stories with signals dict
    - `test_discover_personalized`: Filters by profile keywords + boosts expert content
    - `test_discover_search`: Algolia search with focus modes (practical/debate/expert)
    - `test_trust_find_experts`: Given topic, returns ranked experts with trust scores
    - `test_trust_expert_content_boosted`: Seed expert's stories rank higher
    - `test_understand_story_brief`: Single call returns story + top comments + signals + expert highlights
    - `test_understand_signals_present`: Every tool response includes `signals` dict
    - `test_error_handling_404`: Firebase 404 → structured error
    - `test_error_handling_timeout`: Algolia timeout → structured error
    - `test_error_handling_null_item`: Firebase returns null → skip gracefully
    - `test_concurrent_requests`: asyncio.gather for parallel fetches
    - `test_lifespan_shared_client`: httpx client shared across tool calls
  - **Then implement** `hnmcp/server.py`:
    - FastMCP app with `@lifespan` for shared httpx client + cache + trust scores
    - MCP Tools (mapped to 3 primitives):
      **Discover**:
      - `discover_stories(keywords, min_score, hours, limit, focus)` — personalized feed with quality ranking
      - `search(query, min_score, hours, limit)` — Algolia search with signals
      **Trust**:
      - `find_experts(topic, limit)` — discover domain experts via Algolia author+topic search
      - `expert_brief(username, topic)` — expert's profile + topic activity + trust score
      **Understand**:
      - `story_brief(story_id)` — story + top comments + signals + expert highlights in one call
      - `thread_analysis(story_id, expert_only, max_depth)` — hierarchical comments with trust/quality signals
    - Resources:
      - `hn://config` — current profile and settings
      - `hn://trust` — current trust scores for seed experts
    - All tools use shared httpx client from lifespan context
    - All tools include `signals` dict in response
    - `asyncio.Semaphore(10)` for concurrent API call limiting
    - `asyncio.gather` for parallel item fetches
    - Error handling: try/except around all API calls → structured error dicts

  **Must NOT do**:
  - No tool should work without returning `signals`
  - No direct `httpx.AsyncClient()` creation inside tools (use lifespan)
  - No more than 100 API calls per tool invocation
  - No blocking calls

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3, after 8)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 5, 6, 7, 8

  **References**:
  - FastMCP lifespan pattern: `@mcp.lifespan` decorator + `ctx.lifespan_context["client"]`
  - HN Firebase API: `https://hacker-news.firebaseio.com/v0` — `/topstories.json`, `/item/{id}.json`, `/user/{id}.json`
  - HN Algolia API: `https://hn.algolia.com/api/v1/search` — `tags=comment,author_{username}`, `query={topic}`
  - `hnmcp/quality.py` — `calculate_signals()`, `calculate_quality_score()`
  - `hnmcp/trust.py` — `compute_eigentrust()`, `is_trusted()`, `get_trust_score()`
  - `hnmcp/cache.py` — `TTLCache.get_or_fetch()`
  - `hnmcp/profiles.py` — `load_profile()`
  - `hnmcp/embeddings.py` — `EmbeddingStore` (optional, check if available)

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_server.py` — all 12 tests pass
  - [ ] Every tool response contains `signals` dict
  - [ ] Shared httpx client verified (not creating new per call)
  - [ ] Error responses are structured dicts (not exceptions)
  - [ ] 6 tools + 2 resources registered

  **QA Scenarios**:
  ```
  Scenario: Discover returns stories with signals
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_server.py::test_discover_top_stories -v`
      2. Assert PASSED
      3. Verify response fixture contains "signals" key with 5 sub-keys
    Expected Result: Stories returned with full signal breakdown
    Evidence: .sisyphus/evidence/task-10-discover.txt

  Scenario: Expert content boosted
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_server.py::test_trust_expert_content_boosted -v`
      2. Assert PASSED
    Expected Result: Seed expert's story ranks higher than similar non-expert story
    Evidence: .sisyphus/evidence/task-10-trust-boost.txt

  Scenario: API error handled gracefully
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_server.py::test_error_handling_404 -v`
      2. Assert PASSED
    Expected Result: Structured error dict returned, no exception
    Evidence: .sisyphus/evidence/task-10-error.txt
  ```

  **Commit**: YES
  - Message: `feat(server): MCP tools with lifespan, shared client, and 3-primitives API`
  - Files: `hnmcp/server.py`, `tests/test_server.py`
  - Pre-commit: `pytest tests/test_server.py`

---

- [ ] 11. Integration Tests

  **What to do**:
  - Create `tests/test_integration.py`:
    - `test_full_workflow_discover_to_brief`: discover_stories → pick top result → story_brief → verify all signals present
    - `test_expert_discovery_to_content`: find_experts("security") → expert_brief(top_expert) → verify trust score
    - `test_profile_affects_ranking`: Load profile with keywords → verify stories matching keywords rank higher
    - `test_cache_hit_on_repeat`: Call same tool twice → second call faster (mock verifies fewer API calls)
    - `test_embeddings_optional`: Server starts and all non-embedding tools work without sentence-transformers
    - `test_error_recovery`: API fails mid-request → partial results returned with error context
    - `test_deleted_items_handled`: Comment tree contains deleted items → gracefully skipped
  - All tests use `respx` to mock HN APIs end-to-end
  - Verify module integration (cache → quality → trust → server pipeline)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 13
  - **Blocked By**: Task 10

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_integration.py` — all 7 tests pass
  - [ ] Full pipeline verified: discover → trust → understand
  - [ ] Cache reduces API calls on repeat
  - [ ] Server works without embeddings

  **QA Scenarios**:
  ```
  Scenario: Full pipeline integration
    Tool: Bash
    Steps:
      1. Run `pytest tests/test_integration.py -v`
      2. Assert all 7 tests PASSED
    Expected Result: All cross-module interactions verified
    Evidence: .sisyphus/evidence/task-11-integration.txt
  ```

  **Commit**: YES
  - Message: `test: add integration tests for full discover→trust→understand pipeline`
  - Files: `tests/test_integration.py`
  - Pre-commit: `pytest --cov=hnmcp`

- [ ] 12. Examples + Config Migration

  **What to do**:
  - Update `examples/claude_desktop_config.json` with new entry point (`python -m hnmcp`)
  - Update `examples/README.md`:
    - New config format
    - Migration guide from v1 (change `args` path)
    - Profile file examples for different domains (AI/ML, Security, Startups, Rust)
    - Updated usage examples with new tool names (`discover_stories`, `find_experts`, `story_brief`)
    - Expert recommendations by domain
  - Create `examples/profile.json` — sample profile file

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 11)
  - **Parallel Group**: Wave 4
  - **Blocks**: Final wave
  - **Blocked By**: Task 10

  **Acceptance Criteria**:
  - [ ] `examples/profile.json` is valid JSON with all profile fields
  - [ ] `examples/README.md` contains migration guide
  - [ ] Config uses `python -m hnmcp` entry point

  **QA Scenarios**:
  ```
  Scenario: Example profile is valid
    Tool: Bash
    Steps:
      1. Run `python -c "import json; json.load(open('examples/profile.json'))"`
      2. Assert exit code 0
    Expected Result: Valid JSON
    Evidence: .sisyphus/evidence/task-12-profile.txt
  ```

  **Commit**: YES
  - Message: `docs: update examples with new config format and migration guide`
  - Files: `examples/`

- [ ] 13. Final QA + Coverage

  **What to do**:
  - Run full test suite: `pytest --cov=hnmcp --cov-fail-under=90 -v`
  - Fix any failing tests or coverage gaps
  - Verify `python -m hnmcp` starts server (use respx to mock startup API calls if needed)
  - Verify `pip install -e .` from clean state
  - Run `ruff check hnmcp/` and `black --check hnmcp/`
  - Check for forbidden patterns: `X | Y` syntax, `as any`, live API calls in tests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after Task 11)
  - **Blocks**: Final wave
  - **Blocked By**: Task 11

  **Acceptance Criteria**:
  - [ ] `pytest --cov=hnmcp --cov-fail-under=90` passes
  - [ ] `ruff check hnmcp/` — no errors
  - [ ] `python -m hnmcp` starts without error
  - [ ] No `X | Y` syntax in codebase
  - [ ] No live API calls in any test file

  **QA Scenarios**:
  ```
  Scenario: Full coverage check
    Tool: Bash
    Steps:
      1. Run `pytest --cov=hnmcp --cov-fail-under=90 -v`
      2. Assert exit code 0
      3. Assert "90%" or higher in coverage output
    Expected Result: All tests pass, 90%+ coverage
    Evidence: .sisyphus/evidence/task-13-coverage.txt

  Scenario: Lint check
    Tool: Bash
    Steps:
      1. Run `ruff check hnmcp/`
      2. Assert exit code 0 (no violations)
    Expected Result: Clean linting
    Evidence: .sisyphus/evidence/task-13-lint.txt
  ```

  **Commit**: YES
  - Message: `chore: final QA pass, coverage verification, lint clean`
  - Files: any fixes needed
  - Pre-commit: `pytest --cov=hnmcp --cov-fail-under=90`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest --cov=hnmcp --cov-fail-under=90`. Review all changed files for: `as any`, empty catches, print statements in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify module dependency direction matches plan.
  Output: `Coverage [N%] | Files [N clean/N issues] | Deps [CLEAN/VIOLATION] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task. Test cross-module integration. Test edge cases: empty profile, no experts configured, deleted HN items, API errors. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

| # | Message | Files | Pre-commit |
|---|---------|-------|------------|
| 1 | `scaffold: project structure and test infrastructure` | hnmcp/__init__.py, __main__.py, tests/conftest.py, delete hnmcp.py | — |
| 2 | `chore: update pyproject.toml with new deps and entry points` | pyproject.toml | pip install -e . |
| 3 | `docs: rewrite README with philosophy and 3-primitives` | README.md | — |
| 4 | `feat(cache): TTL cache with async-safe access` | hnmcp/cache.py, tests/test_cache.py | pytest tests/test_cache.py |
| 5 | `feat(profiles): profile loading with env var fallback` | hnmcp/profiles.py, tests/test_profiles.py | pytest tests/test_profiles.py |
| 6 | `feat(quality): 5-signal quality scoring with explainability` | hnmcp/quality.py, tests/test_quality.py | pytest tests/test_quality.py |
| 7 | `feat(trust): EigenTrust with seed expert propagation` | hnmcp/trust.py, tests/test_trust.py | pytest tests/test_trust.py |
| 8 | `feat(server): MCP tools with lifespan and shared client` | hnmcp/server.py, tests/test_server.py | pytest tests/test_server.py |
| 9 | `feat(embeddings): optional semantic similarity search` | hnmcp/embeddings.py, tests/test_embeddings.py | pytest tests/test_embeddings.py |
| 10 | `test: integration tests and final QA` | tests/test_integration.py | pytest --cov=hnmcp --cov-fail-under=90 |
| 11 | `docs: update examples and config migration` | examples/, README.md | — |

---

## Success Criteria

### Verification Commands
```bash
pip install -e ".[dev]"                    # Expected: success
python -m hnmcp                            # Expected: MCP server starts
pytest --cov=hnmcp --cov-fail-under=90     # Expected: all pass, 90%+ coverage
```

### Final Checklist
- [ ] All "Must Have" features implemented and tested
- [ ] All "Must NOT Have" patterns absent from codebase
- [ ] Every tool response includes `signals` dict
- [ ] EigenTrust produces correct trust scores on mock data
- [ ] Profile fallback chain works (JSON → env → defaults)
- [ ] Embeddings are truly optional (server works without sentence-transformers)
- [ ] README explains Why, 3 primitives, setup, examples
- [ ] `python -m hnmcp` starts server successfully
