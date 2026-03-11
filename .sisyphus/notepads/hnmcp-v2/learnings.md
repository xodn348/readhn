- Embeddings feature can remain optional by lazy-loading sentence-transformers in a function, not at module import time.
- Session-scoped semantic search is simple with an in-memory store and cosine similarity over cached vectors.

- 2026-03-10: EigenTrust implementation converged reliably with seeded self-weighting (`_SEED_SELF_WEIGHT=4.0`), plus dangling-node redistribution to pre-trust. This kept seed experts ranked highest while preserving propagation to direct/indirect repliers.
- 2026-03-10: `build_reply_graph` works best as `parent_author -> reply_author` for v2 binary seed propagation semantics.
- 2026-03-10: FastMCP `call_tool` tests do not populate `Context.lifespan_context` by default, so server tools need a shared lazy fallback runtime to reuse one `httpx.AsyncClient` across calls while still supporting lifespan-provided state.
- 2026-03-10: Discover/search ranking can safely combine `calculate_signals` + `calculate_quality_score` with explicit keyword/expert boosts to satisfy personalization tests where lower-score expert stories should outrank generic high-score stories.
- 2026-03-10: Trust tools can share a two-stage Algolia flow (topic comment seed -> per-author `tags=comment,author_<user>`) to compute stable expert rankings from comment volume + practitioner score + trust score, while still exposing aggregate `signals`.
- 2026-03-10: `expert_brief` should tolerate missing Firebase user payloads by returning an empty `profile` but still providing topic-filtered recent comments with per-comment and aggregate `signals`.

- Added understand-layer helpers for recursive comment subtree fetch and depth-map computation so both  and  can share consistent hierarchy/signal context.
- Added  with ranked top comments, expert highlights, and aggregate signals from story+comments to keep one-call explainability stable.
- Added  returning a depth-limited hierarchical tree with per-node quality/trust signals and optional expert-only filtering.
- Added JSON resources  and  via  using runtime profile/trust state for introspection parity with tools.
- Wrapped upstream fetch calls behind  and normalized  to structured error objects (, , ) to satisfy error-path tests when mocks raise exceptions directly.

- 2026-03-10: Added shared recursive comment subtree and depth-map helpers so story_brief and thread_analysis compute hierarchy-aware signals consistently.
- 2026-03-10: story_brief now returns story metadata, ranked top comments, expert highlights, and aggregate signals in one response.
- 2026-03-10: thread_analysis now returns nested comment trees with depth gating, expert_only filtering, per-node quality/trust, and aggregate signals.
- 2026-03-10: Added resource handlers for hn://config and hn://trust that return JSON strings from current runtime profile and trust cache.
- 2026-03-10: Added safe fetch wrapper plus structured error payloads to preserve tool-level error responses when mocked fetches raise HTTPStatusError or TimeoutException.

- Added `tests/test_integration.py` with 7 async end-to-end tests using `respx` HTTP mocking through real `httpx` calls (no live HN traffic).
- Verified discover→trust→understand pipeline by chaining `discover_stories`, `find_experts`, `expert_brief`, and `story_brief` within integration scenarios.
- Confirmed cache integration by asserting repeated `discover_stories` invocations hit Firebase routes once via `respx` call counters.
- Documented error resilience behavior: partial results are returned when some item fetches fail, while direct failed brief requests include HTTP error context.
- Validated deleted/dead comments are filtered in recursive subtree fetch and do not appear in `story_brief` output.
## QA Check Results (Tue Mar 10 19:33:00 CDT 2026)

### Test Coverage: ✅ PASS
- Coverage: 100.00% (target: 90%)
- Tests passed: 199/199
- Excluded: hnmcp/__main__.py (subprocess entry point)

### Server Startup: ✅ PASS
- `python -m hnmcp` starts successfully
- FastMCP 3.1.0 initialized correctly

### Linting: ✅ PASS
- `ruff check hnmcp/` - All checks passed

### Forbidden Patterns: ✅ PASS
- No `X | Y` union syntax found
- No live API calls in tests (all mocked with respx/monkeypatch)

### Test Additions
- Added edge case tests for embeddings (cosine similarity, caching, clear)
- Added trust graph edge case tests (invalid types, missing files, invalid JSON)
- Added server error handling tests (timeout, HTTP errors, generic errors)
- Added fetch_json tests (success, 404, errors)
- Added quality score tests (metrics, zero weights)
- Added __main__.py entry point test

### Coverage Breakdown
- cache.py: 100%
- embeddings.py: 100%
- profiles.py: 100%
- quality.py: 100%
- trust.py: 100%
- server.py: 100%
- Overall: 100.00%
