# devkit-plugin

> Busting Claude's balls - so you don't have to

Claude Code Plugin für automatisierte Dev-Workflows. Deep Code Reviews mit Explore Agents, PR-Workflows mit GitHub Integration, Linter-Sync (ruff, ESLint, markdownlint), und Environment Management.

## Tech Stack

- **Language**: Python 3.10+
- **Runtime**: Claude Code Hooks
- **Framework**: Custom Plugin System
- **Package Manager**: uv

## Project Structure

```
.claude-plugin/  # Plugin manifest
commands/
docs/            # Documentation
hooks/           # Event handlers
skills/          # Agent skills
templates/       # Config templates
tests/           # Test files
```

## Installation

### Via Plugin Manager (recommended)

```bash
# Open plugin manager in Claude Code
/plugin

# Or install directly from marketplace
/plugin install devkit-plugin@your-marketplace
```

### Local Development

```bash
# Load plugin from local directory
claude --plugin-dir /path/to/devkit-plugin

# Or from current directory
claude --plugin-dir .
```

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Check linting
uv run ruff check hooks/

# Security scan
uv run bandit -r hooks/ -q
```

## Documentation

- [Index](docs/INDEX.md) - File overview
- [Architecture](docs/ARCHITECTURE.md) - System design
- [Patterns](docs/PATTERNS.md) - Code patterns
- [Dependencies](docs/DEPENDENCIES.md) - Module graph

## License

MIT

---

*Generated: 2026-01-14*
