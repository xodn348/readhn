# hnmcp

<!-- mcp-name: io.github.xodn348/hnmcp -->

AI-native HackerNews MCP Server. Filter HN through your lens with trust-based expert ranking and explainable quality signals.

## Why

HN is where engineers share lessons that cost them months to learn — in a single comment. tptacek has 4,600+ comments on security. patio11 has written more about SaaS pricing on HN than most books cover. The best engineering knowledge isn't in the stories that get upvoted to the front page. It's buried in comment threads, written by people who've actually built the thing.

The problem is finding it. HN's ranking shows you what's popular, not what's relevant to you. And more importantly — it doesn't tell you who to listen to. On any thread about databases, there might be 200 comments. Three of them are from people who've run Postgres at scale. The rest are opinions. Knowing which three — that's the difference between learning something real and wasting twenty minutes.

hnmcp does three things:

1. **Discover** — Find content that matters to you, not what's trending. Your keywords, your score thresholds, your time window.

2. **Trust** — Know who's talking. hnmcp tracks domain experts, detects practitioner signals ("I built this", "we ran this in production", code blocks, specific metrics), and tells you *why* a comment is worth reading. When you follow experts, their network becomes visible too — people they engage with are probably worth listening to.

3. **Understand** — Every result comes with its reasoning. Not just a score, but the signals behind it: practitioner depth, score velocity, reference density, thread depth, expert involvement. You see why the filter chose what it chose. If it's wrong, you adjust.

**Why AI-native?** Because this isn't a feed to scroll. It's a knowledge base to query. You ask your AI agent "what did practitioners say about Kubernetes networking this week?" and get a structured answer with sources and trust signals — not a list of links.

## Quick Start

```bash
# Install from PyPI
pip install hnmcp

# Optional: with semantic search
pip install hnmcp[embeddings]
```

**That's it!** Your AI agents (Claude Code, OpenCode, Codex) will auto-discover hnmcp from the MCP Registry.

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
    "hnmcp": {
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

**Discover**
- `discover_stories()` - Personalized feed with quality ranking
- `search()` - Algolia search with signals

**Trust**
- `find_experts()` - Discover domain experts
- `expert_brief()` - Expert profile + activity + trust score

**Understand**
- `story_brief()` - Story + top comments + signals in one call
- `thread_analysis()` - Hierarchical comment tree with quality signals

**Resources**
- `hn://config` - Current settings
- `hn://trust` - Trust scores for seed experts

## Quality Signals

Every result explains WHY it was chosen:

- **Practitioner Depth** (30%): "I built", "in production", code blocks, specific metrics
- **Score Velocity** (15%): Points per hour - sustained interest indicator
- **Reference Density** (15%): External links and citations
- **Thread Depth** (20%): Comment tree depth (3+ levels = serious discussion)
- **Expert Involvement** (20%): Participation by followed users

## License

MIT
