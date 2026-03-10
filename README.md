# readhn

<!-- mcp-name: io.github.xodn348/readhn -->

AI-native HackerNews MCP Server. Find HN content that matters with explainable quality signals.

## What It Does

**Discover** — Filter stories by keywords, scores, time. Get ranked results with quality signals.

**Trust** — Find domain experts. See who's talking and why they matter. EigenTrust propagation from seed experts.

**Understand** — Every result explains WHY. 5 signals: practitioner depth (30%), thread depth (20%), expert involvement (20%), velocity (15%), references (15%).

## Quick Start

```bash
# Install from PyPI
pip install readhn

# Optional: with semantic search
pip install readhn[embeddings]
```

**That's it!** Your AI agents (Claude Code, OpenCode, Codex) will auto-discover readhn from the MCP Registry.

### Configuration (Optional)

Set environment variables to customize:

```bash
export HN_KEYWORDS="ai,python,startups"
export HN_MIN_SCORE="50"
export HN_EXPERTS="patio11,tptacek,simonw"
export HN_TIME_HOURS="24"
```

Or configure manually in your agent's MCP config:

```json
{
  "mcpServers": {
    "readhn": {
      "command": "python",
      "args": ["-m", "hnmcp"],
      "env": {
        "HN_KEYWORDS": "ai,python",
        "HN_EXPERTS": "patio11,tptacek"
      }
    }
  }
}
```

## Tools

- `discover_stories()` — Personalized feed with quality ranking
- `search()` — Algolia search with signals
- `find_experts()` — Discover domain experts
- `expert_brief()` — Expert profile + activity + trust score
- `story_brief()` — Story + top comments + signals
- `thread_analysis()` — Comment tree with quality signals

**Resources:** `hn://config` (settings), `hn://trust` (trust scores)

## License

MIT
