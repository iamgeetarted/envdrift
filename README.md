# envdrift

**Multi-environment variable drift detector with live Rich UI and AI remediation advice.**

`envdrift` compares `.env` files across environments (dev / staging / prod), instantly flags missing, extra, and changed variables, masks secret values, and streams AI-powered remediation advice — all with a live terminal dashboard powered by Rich.

## Breakthrough techniques

| Technique | Where |
|---|---|
| **Full async architecture** | `parser.py` — `asyncio.TaskGroup` reads all .env files concurrently; `asyncio.to_thread` keeps file I/O off the event loop |
| **Live Rich UI** | `cli.py` — `Rich.Live` context shows real-time parse status as each environment resolves concurrently |
| **LLM integration** | `advisor.py` — Claude Haiku streaming delivers context-aware remediation advice in real-time |

---

## Install

```bash
pip install envdrift
# or from source:
git clone https://github.com/iamgeetarted/envdrift
cd envdrift && pip install -e .
```

Requires Python ≥ 3.11. Set `ANTHROPIC_API_KEY` for AI features.

---

## Usage

### Auto-discovery

Run `envdrift` in a directory containing `.env`, `.env.staging`, `.env.prod`, etc. and it auto-discovers them:

```bash
envdrift
```

### Explicit environments

```bash
envdrift dev=.env staging=.env.staging prod=.env.prod
```

### With AI advice

```bash
export ANTHROPIC_API_KEY=sk-ant-...
envdrift dev=.env staging=.env.staging --ai
```

### JSON output (for CI pipelines)

```bash
envdrift dev=.env staging=.env.staging --format json | jq '.[] | select(.missing | length > 0)'
```

### List variables in a file

```bash
envdrift list dev=.env
envdrift list dev=.env --secrets   # show unmasked values
```

---

## Sample output

```
┌─ Environments ──────────────────────────────────────────┐
│  Environment  File               Variables  Errors      │
│  dev          .env                      12       0      │
│  staging      .env.staging              10       0      │
│  prod         .env.prod                 11       0      │
└─────────────────────────────────────────────────────────┘

╭─ Drift: dev → staging  (3 issues) ──────────────────────╮
│  Kind     Key              in dev          in staging    │
│  MISSING  REDIS_URL        redis://loc…    not set       │
│  MISSING  FEATURE_FLAGS    true            not set       │
│  CHANGED  DATABASE_URL     postgres://l…   postgres://s… │
╰──────────────────────────────────────────────────────────╯

╭─ Drift: dev → prod  (1 issue) ──────────────────────────╮
│  Kind     Key          in dev           in prod          │
│  EXTRA    DEBUG_MODE   not set          true             │
╰──────────────────────────────────────────────────────────╯
```

With `--ai`:
```
╭─ AI Remediation Advice ─────────────────────────────────╮
╰──────────────────────────────────────────────────────────╯

- **REDIS_URL** (MISSING in staging/prod) — this is likely critical if your app uses
  Redis for sessions or caching; add it to both environment files immediately.
- **FEATURE_FLAGS** being missing in staging suggests it may fall back to a default,
  but verify this is intentional before promoting to prod.
- **DEBUG_MODE=true** in prod is a security risk — remove it or set it to `false`.
```

---

## .env file format

Standard `.env` format is supported:

```bash
# Comments are ignored
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY="my-super-secret-key"
export EXPORTED_VAR=value   # 'export' prefix is stripped
```

Secret-looking keys (`SECRET`, `PASSWORD`, `TOKEN`, `KEY`, `AUTH`, etc.) are automatically masked in output.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No drift detected |
| `1` | Drift found (use in CI to fail builds) |

---

## Architecture

```
envdrift/
├── cli.py       # argparse entrypoint, async orchestration, live Rich progress
├── parser.py    # asyncio.TaskGroup concurrent .env file parser
├── differ.py    # drift detection: missing / extra / changed classification
├── reporter.py  # Rich tables, panels, masked secret display
└── advisor.py   # Claude Haiku streaming AI remediation advice
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
