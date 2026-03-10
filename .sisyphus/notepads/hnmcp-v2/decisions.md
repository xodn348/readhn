- Chose synchronous EmbeddingStore API with internal in-memory vectors to satisfy session-only scope and avoid introducing async requirements to callers.
- Used hnmcp.cache.TTLCache for text and item embedding caching within process session.

- 2026-03-10: Capped trust computation to `MAX_TRUST_USERS` with deterministic seed-first inclusion, then sorted remainder, to guarantee seed experts are retained under large graphs.
- 2026-03-10: Trust cache persistence uses JSON at configurable path (supports `~/.hnmcp/trust_cache.json`) and updates module in-memory cache on compute/load.
