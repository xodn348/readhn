# hnmcp Configuration Examples

## Claude Desktop Setup

1. **Locate your Claude Desktop config file:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add hnmcp to your config:**

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

3. **Customize environment variables:**

## Migration from v1

If you're upgrading from hnmcp v1, update your config:

**Old (v1):**
```json
{
  "args": ["/full/path/to/hnmcp.py"]
}
```

**New (v2):**
```json
{
  "command": "python",
  "args": ["-m", "hnmcp"]
}
```

The new entry point uses Python's module execution (`python -m hnmcp`), which is more portable and doesn't require absolute paths.

## Environment Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `HN_KEYWORDS` | `"ai,python,rust,startups"` | Topics you want to follow (comma-separated) |
| `HN_MIN_SCORE` | `"50"` | Minimum story score to consider |
| `HN_EXPERTS` | `"patio11,simonw,tptacek"` | HN users you trust (comma-separated) |
| `HN_TIME_HOURS` | `"24"` | How far back to search (in hours) |

## Example Configurations

### For AI/ML Engineers
```json
{
  "HN_KEYWORDS": "ai,machine learning,llm,gpt,transformers,pytorch",
  "HN_MIN_SCORE": "30",
  "HN_EXPERTS": "simonw,karpathy,jeffdean",
  "HN_TIME_HOURS": "48"
}
```

### For Startup Founders
```json
{
  "HN_KEYWORDS": "startup,saas,business,monetization,growth",
  "HN_MIN_SCORE": "50",
  "HN_EXPERTS": "patio11,edwardkmett,sama",
  "HN_TIME_HOURS": "24"
}
```

### For Security Professionals
```json
{
  "HN_KEYWORDS": "security,cryptography,vulnerability,infosec",
  "HN_MIN_SCORE": "40",
  "HN_EXPERTS": "tptacek,cperciva,veorq",
  "HN_TIME_HOURS": "72"
}
```

### For Rust Developers
```json
{
  "HN_KEYWORDS": "rust,cargo,wasm,systems programming",
  "HN_MIN_SCORE": "20",
  "HN_EXPERTS": "steveklabnik,withoutboats,burntsushi",
  "HN_TIME_HOURS": "48"
}
```

## Usage in Claude Desktop

Once configured, restart Claude Desktop and try:

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

```
User: "Find practical Rust advice from this week"

Claude: [calls discover_stories(keywords="rust", focus="practical")]
```

```
User: "What has patio11 said recently?"

Claude: [calls expert_brief("patio11")]
```

```
User: "Summarize this HN thread"

Claude: [calls story_brief(story_id)]
```

## Recommended Experts by Domain

**General Engineering:**
- patio11 (Patrick McKenzie) - SaaS, business, monetization
- simonw (Simon Willison) - AI/ML, Python, practical tools
- tptacek (Thomas Ptacek) - Security, cryptography
- dang (Daniel Gackle) - HN moderation, culture

**Systems & Performance:**
- cperciva (Colin Percival) - FreeBSD, security
- brendangregg - Performance, observability
- brson - Rust, systems programming

**AI/ML:**
- karpathy (Andrej Karpathy) - Deep learning, LLMs
- jeffdean (Jeff Dean) - Google AI, distributed systems
- fchollet (François Chollet) - Keras, AI research

**Web/Frontend:**
- tj (TJ Holowaychuk) - Node.js, tooling
- rauchg (Guillermo Rauch) - Vercel, Next.js

**Databases:**
- antirez (Salvatore Sanfilippo) - Redis
- markokr - PostgreSQL

**Startups:**
- sama (Sam Altman) - YC, OpenAI
- paulg (Paul Graham) - YC, essays

## Tips

1. **Start broad, then narrow:** Begin with general keywords, then refine based on what you find useful
2. **Adjust MIN_SCORE by topic:** Niche topics (Rust) may need lower scores, popular topics (AI) need higher
3. **Follow diverse voices:** Mix technical experts with business/product thinkers
4. **Experiment with TIME_HOURS:** 24h for daily digest, 72h for weekly deep dive
