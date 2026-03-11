# readhn

<!-- mcp-name: io.github.xodn348/readhn -->

[![PyPI](https://badge.fury.io/py/readhn.svg)](https://pypi.org/project/readhn/)
[![Tests](https://img.shields.io/badge/tests-137%20passed-brightgreen)](https://github.com/xodn348/readhn)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://github.com/xodn348/readhn)
[![MCP](https://img.shields.io/badge/MCP-Registry-blue)](https://registry.modelcontextprotocol.io/v0.1/servers?search=readhn)

AI-native HackerNews MCP Server. Find HN content that matters with explainable quality signals.

## What It Does

**Discover** — Filter stories by keywords, scores, time. Get ranked results with quality signals.

**Trust** — Find domain experts. See who's talking and why they matter. EigenTrust propagation from seed experts.

**Understand** — Every result explains WHY. 5 signals: practitioner depth (30%), thread depth (20%), expert involvement (20%), velocity (15%), references (15%).

## Quick Start

```bash
# Install
pip install readhn

# Auto-configure supported AI agents
readhn setup
```

`readhn setup` detects Claude Code, Codex, Cursor, Claude Desktop, Cline, Windsurf, and OpenCode config paths and adds the `readhn` MCP server.

Useful setup flags:

```bash
readhn setup --list              # Show detected agents
readhn setup --dry-run           # Preview config changes only
readhn setup --agents "Cursor"  # Configure only specific agents
```

After setup, your AI agent auto-discovers readhn and uses it when you ask HN questions.

### Usage

Ask your AI agent:
- "Show me top HN stories about Rust this week"
- "Find experts who write about databases on HN"
- "What did practitioners say about Kubernetes networking?"

The agent calls readhn tools, gets results with quality signals, and explains why each result matters.

### Configuration (Optional)

```bash
export HN_KEYWORDS="ai,llm,rust,distributed-systems,databases"  # Default filter keywords
export HN_MIN_SCORE="50"                                         # Minimum story score
export HN_EXPERTS="tptacek,simonw,antirez,ept,jepsen"           # Seed experts for trust
export HN_TIME_HOURS="24"                                        # Time window
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
