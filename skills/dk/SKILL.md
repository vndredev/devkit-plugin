---
name: dk
description: "CRITICAL: YOU MUST use this skill for ANY code changes via /dk dev workflow. Also handles: /dk git (PRs, branches), /dk plugin (health check, sync), /dk env (secrets), /dk vercel (deploy), /dk neon (database). Routes to reference docs."
allowed-tools: TodoWrite, Read, Write, Edit, Bash(python3:*), Bash(git:*), Bash(gh:*), Bash(ruff:*), Bash(uv:*), Bash(npm:*), Bash(npx:*), Bash(vercel:*), Bash(neonctl:*), Bash(psql:*), Task, Grep, Glob
---

# DK Skill

**CRITICAL:** Unified devkit-plugin interface. YOU MUST use `/dk` commands for ALL workflows.

## Workflow Enforcement

**The plugin enforces proper git workflow through hooks:**

| Hook            | When               | Action                                    |
| --------------- | ------------------ | ----------------------------------------- |
| `SessionStart`  | Session begins     | ⚠️ Warns if on protected branch           |
| `EnterPlanMode` | Before plan mode   | ⚠️ Warns or 🚫 blocks on protected branch |
| `Write/Edit`    | After code changes | ⚠️ Warns if editing code on main          |

**Configuration:** `hooks.plan.enforce_workflow` (`warn`, `block`, `off`)

### When to Use Which Command

| I want to...                    | Use this command                  |
| ------------------------------- | --------------------------------- |
| Start working on code           | `/dk dev feat\|fix\|chore <desc>` |
| Analyze code for issues         | `/dk analyze`                     |
| Create a PR after coding        | `/dk git pr`                      |
| Check plugin health             | `/dk plugin check`                |
| Sync files after config changes | `/dk plugin update`               |

**If you're on `main` and try to enter Plan Mode, the hook will warn you!**

## MANDATORY Rules

**YOU MUST follow these rules at ALL times:**

1. **ALWAYS start with `/dk dev`** - Before ANY code work, use `/dk dev feat|fix|chore <desc>` to create a feature branch.
2. **ALWAYS return to main after PR** - `/dk git pr` auto-returns to main. Verify with `git branch` before starting new work.
3. **ALWAYS use `/dk git pr`** for pull requests - NEVER use raw `gh pr create`
4. **ALWAYS use `/dk dev`** for development workflows - NEVER skip the workflow
5. **ALWAYS use `/dk vercel deploy`** for deployments - NEVER use raw `vercel deploy`
6. **NEVER execute raw git/gh commands** when a `/dk` equivalent exists
7. **ALWAYS read CLAUDE.md** before making code changes
8. **FIX LAYER VIOLATIONS IMMEDIATELY** - If you see "🚫 LAYER VIOLATION" in hook output, you MUST fix it NOW before continuing. Layer rules enforce Clean Architecture - higher tiers cannot import from lower tiers.
9. **ALWAYS show full output** - After every Bash command, repeat the COMPLETE output in a formatted Markdown code block. Claude Code truncates output, so you MUST show it again for the user.
10. **ALWAYS offer `/dk git pr`** - After completing code changes, ALWAYS ask: "Soll ich einen PR erstellen? (`/dk git pr`)" - This ensures changes get properly reviewed and merged.

## Commands

| Command                    | Reference   | Description                         |
| -------------------------- | ----------- | ----------------------------------- |
| `/dk`                      | -           | Show status and available commands  |
| `/dk plugin`               | plugin.md   | Quick plugin status                 |
| `/dk plugin check`         | plugin.md   | Full health check                   |
| `/dk plugin update`        | plugin.md   | Sync all managed files              |
| `/dk plugin init`          | plugin.md   | Initialize new project              |
| `/dk plugin marketplace`   | plugin.md   | Show marketplace status (dev/prod)  |
| `/dk plugin publish`       | plugin.md   | Update prod version in marketplace  |
| `/dk plugin dev`           | plugin.md   | Setup local dev override            |
| `/dk dev feat <desc>`      | dev.md      | Develop new feature                 |
| `/dk dev fix <desc>`       | dev.md      | Fix a bug                           |
| `/dk dev chore <desc>`     | dev.md      | Maintenance task                    |
| `/dk dev refactor <desc>`  | dev.md      | Code refactoring                    |
| `/dk dev test <desc>`      | dev.md      | Add tests                           |
| `/dk dev docs <desc>`      | dev.md      | Documentation changes               |
| `/dk dev quick <desc>`     | dev.md      | Quick small change (typo, tweak)    |
| `/dk analyze`              | analyze.md  | Deep Opus analysis with plan        |
| `/dk analyze quick`        | analyze.md  | Quick single-agent analysis         |
| `/dk analyze fix`          | analyze.md  | Continue fixing from existing plan  |
| `/dk analyze system`       | analyze.md  | Full system audit                   |
| `/dk analyze system quick` | analyze.md  | Quick system audit (core only)      |
| `/dk git`                  | git.md      | Git workflow help                   |
| `/dk git init`             | git.md      | Initialize new project (full setup) |
| `/dk git update`           | git.md      | Sync files and GitHub settings      |
| `/dk git pr`               | git.md      | Create pull request                 |
| `/dk git pr review [n]`    | git.md      | Check PR review comments            |
| `/dk git pr merge [n]`     | git.md      | Merge PR (squash)                   |
| `/dk git branch <name>`    | git.md      | Create feature branch               |
| `/dk git squash`           | git.md      | Squash commits                      |
| `/dk git cleanup`          | git.md      | Clean local tags + branches         |
| `/dk git issue report`     | git.md      | Report bug in devkit-plugin         |
| `/dk git issue create`     | git.md      | Create issue in current project     |
| `/dk git issue list`       | git.md      | List open issues                    |
| `/dk git issue view [n]`   | git.md      | View issue details                  |
| `/dk env`                  | env.md      | Environment sync help               |
| `/dk env sync`             | env.md      | Sync .env to Vercel + GitHub        |
| `/dk env pull`             | env.md      | Pull env vars from Vercel           |
| `/dk env list`             | env.md      | List env vars                       |
| `/dk env clean`            | env.md      | Remove unused env vars              |
| `/dk vercel`               | vercel.md   | Vercel deployment help              |
| `/dk vercel connect`       | vercel.md   | Link project to Vercel              |
| `/dk vercel status`        | vercel.md   | Show Vercel project status          |
| `/dk vercel deploy`        | vercel.md   | Deploy to preview                   |
| `/dk vercel env`           | vercel.md   | Manage Vercel env vars              |
| `/dk vercel env sync`      | vercel.md   | Sync .env.local to Vercel           |
| `/dk vercel env pull`      | vercel.md   | Pull env vars from Vercel           |
| `/dk neon`                 | neon.md     | NeonDB branch management            |
| `/dk neon branch list`     | neon.md     | List NeonDB branches                |
| `/dk neon branch create`   | neon.md     | Create NeonDB branch                |
| `/dk neon branch delete`   | neon.md     | Delete NeonDB branch                |
| `/dk neon branch switch`   | neon.md     | Switch NeonDB branch                |
| `/dk neon cleanup`         | neon.md     | Clean stale branches                |
| `/dk arch`                 | arch.md     | Architecture overview               |
| `/dk arch analyze`         | arch.md     | Analyze dependencies                |
| `/dk arch check`           | arch.md     | Check layer rule compliance         |
| `/dk arch discover <name>` | arch.md     | Find similar code before writing    |
| `/dk arch init [type]`     | arch.md     | Scaffold Clean Architecture         |
| `/dk arch layers`          | arch.md     | Show layer documentation            |
| `/dk serv`                 | serv.md     | Service status (dev + webhooks)     |
| `/dk serv start`           | serv.md     | Start all dev services              |
| `/dk serv stop`            | serv.md     | Stop all services                   |
| `/dk serv urls`            | serv.md     | Show all URLs                       |
| `/dk serv test`            | serv.md     | Send test events                    |
| `/dk webhooks`             | webhooks.md | Webhook configuration status        |
| `/dk docs`                 | docs.md     | Show docs status (all files)        |
| `/dk docs update`          | docs.md     | Update all docs from config         |
| `/dk docs init`            | docs.md     | Create missing docs                 |
| `/dk docs arch`            | docs.md     | Generate/update ARCHITECTURE.md     |
| `/dk docs plugin`          | docs.md     | Generate/update PLUGIN.md           |
| `/dk docs claude`          | docs.md     | Generate/update CLAUDE.md           |
| `/dk axiom`                | axiom.md    | Axiom status + auth                 |
| `/dk axiom login`          | axiom.md    | Authenticate with Axiom             |
| `/dk axiom datasets`       | axiom.md    | List/manage datasets                |
| `/dk axiom query`          | axiom.md    | Execute APL query                   |
| `/dk axiom stream`         | axiom.md    | Livestream logs                     |
| `/dk axiom web`            | axiom.md    | Open dashboard                      |
| `/dk axiom token`          | axiom.md    | Token management                    |
| `/dk axiom test`           | axiom.md    | Test connectivity                   |
| `/dk livekit`              | livekit.md  | LiveKit status + auth               |
| `/dk livekit room list`    | livekit.md  | List active rooms                   |
| `/dk livekit room create`  | livekit.md  | Create room                         |
| `/dk livekit token`        | livekit.md  | Generate access token               |
| `/dk livekit web`          | livekit.md  | Open cloud dashboard                |
| `/dk browser`              | browser.md  | Browser status + help               |
| `/dk browser verify`       | browser.md  | Full UI verification flow           |
| `/dk browser screenshot`   | browser.md  | Take screenshot of current page     |
| `/dk browser open <url>`   | browser.md  | Open URL in browser                 |
| `/dk mcp`                  | mcp.md      | MCP server status                   |

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
    "analyze": "reference/analyze.md",
    "git": "reference/git.md",
    "env": "reference/env.md",
    "vercel": "reference/vercel.md",
    "neon": "reference/neon.md",
    "arch": "reference/arch.md",
    "serv": "reference/serv.md",
    "webhooks": "reference/webhooks.md",
    "docs": "reference/docs.md",
    "axiom": "reference/axiom.md",
    "livekit": "reference/livekit.md",
    "browser": "reference/browser.md",
    "mcp": "reference/mcp.md"
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
print('Commands: /dk plugin | dev | analyze | git | arch | docs | env | vercel | neon')
"
```

---

## Reference Loading

**CRITICAL: YOU MUST load and follow the reference instructions for the requested subcommand.**

| Subcommand              | Action                                            |
| ----------------------- | ------------------------------------------------- |
| `/dk plugin [sub]`      | Read `reference/plugin.md`, follow instructions   |
| `/dk dev [type] <desc>` | Read `reference/dev.md`, follow instructions      |
| `/dk analyze [sub]`     | Read `reference/analyze.md`, follow instructions  |
| `/dk git [sub]`         | Read `reference/git.md`, follow instructions      |
| `/dk env [sub]`         | Read `reference/env.md`, follow instructions      |
| `/dk vercel [sub]`      | Read `reference/vercel.md`, follow instructions   |
| `/dk neon [sub]`        | Read `reference/neon.md`, follow instructions     |
| `/dk arch [sub]`        | Read `reference/arch.md`, follow instructions     |
| `/dk serv [sub]`        | Read `reference/serv.md`, follow instructions     |
| `/dk webhooks [sub]`    | Read `reference/webhooks.md`, follow instructions |
| `/dk docs [sub]`        | Read `reference/docs.md`, follow instructions     |
| `/dk axiom [sub]`       | Read `reference/axiom.md`, follow instructions    |
| `/dk livekit [sub]`     | Read `reference/livekit.md`, follow instructions  |
| `/dk browser [sub]`     | Read `reference/browser.md`, follow instructions  |
| `/dk mcp`               | Read `reference/mcp.md`, follow instructions      |

**ALWAYS pass the remaining arguments to the module.**

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

**CRITICAL: YOU MUST follow these rules - NO EXCEPTIONS:**

1. **Derive PLUGIN_ROOT** - YOU MUST extract from Base directory (remove `/skills/dk`)
2. **Parse subcommand** - ALWAYS determine which module to load
3. **Load module file** - YOU MUST read the appropriate .md file BEFORE executing
4. **Replace paths** - YOU MUST substitute `${PLUGIN_ROOT}` with actual path
5. **Execute commands** - YOU MUST follow module instructions EXACTLY as written

## Command Enforcement

**NEVER bypass `/dk` commands:**

| Instead of...         | YOU MUST use...      |
| --------------------- | -------------------- |
| `gh pr create`        | `/dk git pr`         |
| `vercel deploy`       | `/dk vercel deploy`  |
| `git commit` (manual) | Conventional commits |
| Direct file editing   | `/dk dev` workflow   |

**ALWAYS use TodoWrite** to track progress during multi-step tasks.
