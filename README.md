# hnmcp

**AI-native HackerNews MCP Server**

Read HackerNews through your lens, not the algorithm's. An MCP server that filters, interprets, and surfaces HN content based on your interests, preferred experts, and quality signals.

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

## Quick Start

### Installation

```bash
pip install -e .
# Or with optional embeddings support:
pip install -e ".[embeddings]"
```

### Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hackernews": {
      "command": "python",
      "args": ["-m", "hnmcp"],
      "env": {
        "HN_KEYWORDS": "ai,machine learning,startups",
        "HN_MIN_SCORE": "50",
        "HN_EXPERTS": "patio11,simonw,tptacek",
        "HN_TIME_HOURS": "24"
      }
    }
  }
}
```

**Migration from v1**: Update your config to use `python -m hnmcp` instead of the old single-file path.

### Usage

Restart Claude Desktop, then:

```
User: "오늘 AI 관련 실전 경험담 찾아줘"

Claude: [calls discover_stories()]
        
        "3개 발견:
        1. [89 pts] 'I built an AI agent for...' 
           - Posted by simonw (following)
           - Practitioner markers: 'I built', 'in production'
        
        2. [67 pts] 'Our LLM debugging story'
           - Code blocks included
           - Specific metrics: '35% improvement'
        ..."
```

## Available Tools

### Discover
- `discover_stories(keywords, min_score, hours, limit, focus)` - Personalized feed with quality ranking
- `search(query, min_score, hours, limit)` - Algolia search with signals

### Trust
- `find_experts(topic, limit)` - Discover domain experts via author+topic search
- `expert_brief(username, topic)` - Expert's profile + topic activity + trust score

### Understand
- `story_brief(story_id)` - Story + top comments + signals + expert highlights in one call
- `thread_analysis(story_id, expert_only, max_depth)` - Hierarchical comments with trust/quality signals

### Resources
- `hn://config` - View current settings
- `hn://trust` - Current trust scores for seed experts

## Quality Signals

Based on proven HN analysis patterns:

- **Practitioner Depth** (30%): Experience markers ("I built", "we used", code blocks)
- **Score Velocity** (15%): Points per hour (sustained interest)
- **Reference Density** (15%): External links and citations
- **Thread Depth** (20%): Comment tree depth (3+ levels = serious discussion)
- **Expert Involvement** (20%): Followed users' participation

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HN_KEYWORDS` | `""` | Comma-separated topics (e.g., "ai,python,startups") |
| `HN_MIN_SCORE` | `0` | Minimum story score |
| `HN_EXPERTS` | `""` | Comma-separated usernames to follow |
| `HN_TIME_HOURS` | `24` | Look back time window |

## Examples

### Find practical AI advice
```
User: "AI 관련 실전 조언만 추려줘"
Claude: [search("AI OR LLM", focus="practical")]
```

### Track expert activity
```
User: "patio11이 최근에 뭐 말했어?"
Claude: [expert_brief("patio11", topic="saas")]
```

### Analyze debate
```
User: "이 스레드 논쟁 요약해줘"
Claude: [thread_analysis(story_id, expert_only=True)]
```

## Architecture

```
User ←→ AI Agent (Claude/GPT) ←→ hnmcp ←→ HN APIs
                                       ├─ Firebase (real-time)
                                       └─ Algolia (search)
```

## License

MIT

## Contributing

PRs welcome! When contributing:
- Keep it AI-native (no web UI as core feature)
- Maintain explainability (expose signals, don't hide them)
- Follow existing async patterns (httpx, FastMCP)

---

**Made with ❤️ for the HN community**
