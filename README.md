# devkit-plugin

> Busting Claude's balls - so you don't have to

Claude Code plugin for automated dev workflows.

- **PR Workflows** - Create, review, merge with one command
- **Auto-Formatting** - ruff, prettier, markdownlint on save
- **Environment Sync** - Vercel, GitHub secrets, NeonDB branches

## Install

```bash
claude plugins:add vndredev/devkit-plugin
```

## Quick Start

```bash
/dk git init                 # Initialize project
/dk dev feat "add login"     # Start feature
/dk git pr                   # Create PR
/dk git pr merge             # Merge (squash)
```

## Features

| Feature | Command | Description |
|---------|---------|-------------|
| Development | `/dk dev` | Feature workflow with branching |
| Git | `/dk git` | PR, branch, issue management |
| Architecture | `/dk arch` | Clean Architecture analysis |
| Environment | `/dk env` | Env var sync to platforms |
| Deployment | `/dk vercel` | Vercel deployment |
| Database | `/dk neon` | NeonDB branch management |

## Configuration

All settings in `.claude/.devkit/config.jsonc`:

```jsonc
{
  "project": { "name": "...", "type": "python" },
  "github": { "pr": { "auto_merge": true, "merge_method": "squash" } },
  "hooks": { "format": { "auto_format": true } }
}
```

## Documentation

- **[Full Reference](docs/PLUGIN.md)** - Complete documentation
- **[CLAUDE.md](CLAUDE.md)** - Project instructions

## Tech Stack

- Python 3.10+ / uv
- Claude Code Hooks
- GitHub Actions

## License

MIT
