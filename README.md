# readhn

<!-- mcp-name: io.github.xodn348/readhn -->

AI-native HackerNews MCP Server. Find HN content that matters with explainable quality signals.

## What It Does

**Discover** — Filter stories by keywords, scores, time. Get ranked results with quality signals.

**Trust** — Find domain experts. See who's talking and why they matter. EigenTrust propagation from seed experts.

**Understand** — Every result explains WHY. 5 signals: practitioner depth (30%), thread depth (20%), expert involvement (20%), velocity (15%), references (15%).

## Quick Start

```bash
# Install
pip install readhn
```

**That's it.** Your AI agent auto-discovers readhn and uses it when you ask HN questions.

### Usage

Ask your AI agent:
- "Show me top HN stories about Rust this week"
- "Find experts who write about databases on HN"
- "What did practitioners say about Kubernetes networking?"

The agent calls readhn tools, gets results with quality signals, and explains why each result matters.

### Configuration (Optional)

```bash
export HN_KEYWORDS="ai,python,startups"    # Default filter keywords
export HN_MIN_SCORE="50"                   # Minimum story score
export HN_EXPERTS="patio11,tptacek,simonw" # Seed experts for trust
export HN_TIME_HOURS="24"                  # Time window
```

## How It Works

When you ask HN questions, your AI agent uses these tools:

- `discover_stories()` — Top stories filtered by keywords/score/time, ranked by quality signals
- `search()` — Algolia search with explainable ranking
- `find_experts()` — Find domain experts using EigenTrust on comment graph
- `expert_brief()` — User profile + activity + trust score
- `story_brief()` — Story + top comments + signals in one call
- `thread_analysis()` — Full comment tree with quality signals per comment

Every response includes signals breakdown: why each result was chosen.

## License

MIT
