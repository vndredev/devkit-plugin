---
name: dk
description: "CRITICAL: YOU MUST use this skill for ANY code changes via /dk dev workflow. Also handles: /dk git (PRs, branches), /dk plugin (health check, sync), /dk env (secrets), /dk vercel (deploy), /dk neon (database). Routes to reference docs."
allowed-tools: TodoWrite, Read, Write, Edit, Bash(python3:*), Bash(git:*), Bash(gh:*), Bash(ruff:*), Bash(uv:*), Bash(npm:*), Bash(npx:*), Bash(vercel:*), Bash(neonctl:*), Bash(psql:*), Task, Grep, Glob
---

# DK Skill

Unified devkit-plugin interface. Routes to reference docs.

## Commands

| Command                   | Reference   | Description                        |
| ------------------------- | ----------- | ---------------------------------- |
| `/dk`                     | -           | Show status and available commands |
| `/dk plugin`              | plugin.md   | Quick plugin status                |
| `/dk plugin check`        | plugin.md   | Full health check                  |
| `/dk plugin update`       | plugin.md   | Sync all managed files             |
| `/dk plugin init`         | plugin.md   | Initialize new project             |
| `/dk dev feat <desc>`     | dev.md      | Develop new feature                |
| `/dk dev fix <desc>`      | dev.md      | Fix a bug                          |
| `/dk dev chore <desc>`    | dev.md      | Maintenance task                   |
| `/dk dev refactor <desc>` | dev.md      | Code refactoring                   |
| `/dk dev test <desc>`     | dev.md      | Add tests                          |
| `/dk git`                 | git.md      | Git workflow help                  |
| `/dk git init`            | git.md      | Initialize new project (full setup)|
| `/dk git update`          | git.md      | Sync files and GitHub settings     |
| `/dk git pr`              | git.md      | Create pull request                |
| `/dk git pr review [n]`   | git.md      | Check PR review comments           |
| `/dk git pr merge [n]`    | git.md      | Merge PR (squash)                  |
| `/dk git branch <name>`   | git.md      | Create feature branch              |
| `/dk git squash`          | git.md      | Squash commits                     |
| `/dk git cleanup`         | git.md      | Clean local tags + branches        |
| `/dk git issue report`    | git.md      | Report bug in devkit-plugin        |
| `/dk git issue create`    | git.md      | Create issue in current project    |
| `/dk git issue list`      | git.md      | List open issues                   |
| `/dk git issue view [n]`  | git.md      | View issue details                 |
| `/dk env`                 | env.md      | Environment sync help              |
| `/dk env sync`            | env.md      | Sync .env to Vercel + GitHub       |
| `/dk env pull`            | env.md      | Pull env vars from Vercel          |
| `/dk env list`            | env.md      | List env vars                      |
| `/dk env clean`           | env.md      | Remove unused env vars             |
| `/dk vercel`              | vercel.md   | Vercel deployment help             |
| `/dk vercel connect`      | vercel.md   | Link project to Vercel             |
| `/dk vercel env`          | vercel.md   | Manage Vercel env vars             |
| `/dk neon`                | neon.md     | NeonDB branch management           |
| `/dk neon branch list`    | neon.md     | List NeonDB branches               |
| `/dk neon branch create`  | neon.md     | Create NeonDB branch               |
| `/dk neon branch delete`  | neon.md     | Delete NeonDB branch               |
| `/dk neon branch switch`  | neon.md     | Switch NeonDB branch               |
| `/dk neon cleanup`        | neon.md     | Clean stale branches               |
| `/dk arch`                | arch.md     | Architecture overview              |
| `/dk arch analyze`        | arch.md     | Analyze dependencies               |
| `/dk arch check`          | arch.md     | Check layer rule compliance        |
| `/dk arch init [type]`    | arch.md     | Scaffold Clean Architecture        |
| `/dk arch layers`         | arch.md     | Show layer documentation           |
| `/dk docs`                | docs.md     | Show CLAUDE.md status              |
| `/dk docs update`         | docs.md     | Update AUTO sections               |
| `/dk docs init`           | docs.md     | Create CLAUDE.md from template     |

---

## Routing Logic

Parse the subcommand and load the appropriate module:

```python
import sys
args = sys.argv[1:] if len(sys.argv) > 1 else []
cmd = args[0] if args else ""

modules = {
    "plugin": "reference/plugin.md",
    "dev": "reference/dev.md",
    "git": "reference/git.md",
    "env": "reference/env.md",
    "vercel": "reference/vercel.md",
    "neon": "reference/neon.md",
    "arch": "reference/arch.md",
    "docs": "reference/docs.md"
}

if cmd in modules:
    print(f"Loading: {modules[cmd]}")
else:
    print("Available: " + ", ".join(modules.keys()))
```

---

## /dk - Status

Shows project status and available commands:

```bash
uv run python -c "
import json
from pathlib import Path
config = json.loads(Path('.claude/.devkit/config.jsonc').read_text())
project = config.get('project', {})
linters = config.get('linters', {})
print(f'Project: {project.get(\"name\", \"unknown\")}')
print(f'Type: {project.get(\"type\", \"unknown\")}')
print(f'Linter preset: {linters.get(\"preset\", \"strict\")}')
print()
print('Commands: /dk plugin | dev | git | arch | docs | env | vercel | neon')
"
```

---

## Reference Loading

**YOU MUST load and follow the reference instructions for the requested subcommand.**

| Subcommand              | Action                                          |
| ----------------------- | ----------------------------------------------- |
| `/dk plugin [sub]`      | Read `reference/plugin.md`, follow instructions |
| `/dk dev [type] <desc>` | Read `reference/dev.md`, follow instructions    |
| `/dk git [sub]`         | Read `reference/git.md`, follow instructions    |
| `/dk env [sub]`         | Read `reference/env.md`, follow instructions    |
| `/dk vercel [sub]`      | Read `reference/vercel.md`, follow instructions |
| `/dk neon [sub]`        | Read `reference/neon.md`, follow instructions   |
| `/dk arch [sub]`        | Read `reference/arch.md`, follow instructions   |
| `/dk docs [sub]`        | Read `reference/docs.md`, follow instructions   |

**Pass the remaining arguments to the module.**

Example: `/dk git pr` → Load `reference/git.md`, execute `/git pr` section.

---

## Plugin Root Path

**CRITICAL: Before executing any module commands, derive PLUGIN_ROOT from the Base directory.**

The "Base directory for this skill" header shows the skill path. Remove `/skills/dk` to get PLUGIN_ROOT:

```
Base directory: /path/to/devkit-plugin/skills/dk
PLUGIN_ROOT:    /path/to/devkit-plugin
```

**YOU MUST** replace `${PLUGIN_ROOT}` in all bash commands with the actual path.

---

## Key Rules (MANDATORY)

**YOU MUST follow these rules:**

1. **Derive PLUGIN_ROOT** - YOU MUST extract from Base directory (remove `/skills/dk`)
2. **Parse subcommand** - Determine which module to load
3. **Load module file** - YOU MUST read the appropriate .md file
4. **Replace paths** - YOU MUST substitute `${PLUGIN_ROOT}` with actual path
5. **Execute commands** - YOU MUST follow module instructions exactly
