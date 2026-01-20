# devkit-plugin - Complete Reference

> Auto-generated documentation. Do not edit manually.

Claude Code plugin for automated dev workflows. PR workflows with GitHub integration, linter sync, and environment management.

## Quick Start

### Installation

```bash
# Install as Claude Code plugin
claude plugins:add vndredev/devkit-plugin
```

### First Run

```bash
# Initialize project
/dk git init

# Show plugin status
/dk
```

### Essential Commands

```bash
/dk dev feat "add login"     # Start feature development
/dk git pr                   # Create pull request
/dk git pr merge             # Merge PR (squash)
```

## Configuration Reference

Location: `.claude/.devkit/config.jsonc`

The config uses JSONC format (JSON with Comments) for better readability.

### Project Identity

```jsonc
"project": {
  "name": "my-project",           // Project name
  "type": "python",               // python | node | nextjs | typescript
  "version": "0.1.0",             // Semantic version
  "slogan": "...",                // Short tagline (optional)
  "description": "...",           // Brief description (optional)
  "principles": ["KISS", "YAGNI"] // Project principles (optional)
}
```

### Git Configuration

```jsonc
"git": {
  "protected_branches": ["main"],  // No force push allowed
  "conventions": {
    "types": ["feat", "fix", "chore", "refactor", "test", "docs", "perf", "ci"],
    "scopes": {
      "mode": "strict",            // strict=error, warn=warning, off=disabled
      "allowed": [],               // Project-specific scopes
      "internal": ["internal", "review", "ci", "deps"]  // Skip release notes
    },
    "branch_pattern": "{type}/{description}"
  }
}
```

### GitHub Settings

```jsonc
"github": {
  "url": "https://github.com/owner/repo",
  "visibility": "public",          // public | private | internal
  "pr": {
    "auto_merge": false,           // Enable auto-merge on PR create
    "delete_branch": true,         // Delete branch after merge
    "merge_method": "squash"       // squash | merge | rebase
  }
}
```

### Quality Configuration

```jsonc
"linters": {
  "preset": "strict",              // strict | relaxed | minimal
  "overrides": {}                  // Override preset values
},
"testing": {
  "enabled": false,
  "framework": "pytest"            // pytest | vitest | jest
}
```

### Hooks

```jsonc
"hooks": {
  "session": {
    "enabled": true,
    "show_git_status": true        // Show status on session start
  },
  "validate": {
    "enabled": true,
    "block_force_push": true,      // Block git push --force
    "block_dangerous_gh": true     // Block gh repo delete, etc.
  },
  "format": {
    "enabled": true,
    "auto_format": true            // Format files after edit
  },
  "plan": {
    "enabled": true                // Inject dev instructions in plan mode
  }
}
```

### Changelog

```jsonc
"changelog": {
  "audience": "developer"          // developer=technical, user=simple
}
```

### Deployment

```jsonc
"deployment": {
  "enabled": true,
  "platform": "vercel",            // vercel | railway | render | fly
  "env_sync": true,                // Sync env vars to platform
  "production_domain": ""          // Production URL
}
```

### Architecture Layers

```jsonc
"arch": {
  "layers": {
    "core": { "tier": 0 },         // Tier 0 = innermost (no deps)
    "lib": { "tier": 1 },          // Higher tiers import lower only
    "events": { "tier": 2 }
  }
}
```

### Consistency Checks

```jsonc
"consistency": {
  "enabled": true,                   // Enable consistency validation
  "rules": {
    "module_tests": {
      "enabled": true,
      "patterns": {                  // Source -> Test file mapping
        "src/lib/*.py": "tests/test_{stem}.py"
      },
      "exclude": ["__init__.py"]     // Files to skip
    },
    "hook_handlers": { "enabled": true },   // Check hooks have handlers
    "config_schema": { "enabled": true },   // Check config keys in schema
    "skill_routes": { "enabled": true },    // Check skill doc references
    "custom_imports": {
      "enabled": false,              // Custom import rules
      "deny": ["src/hooks/* -> @prisma/client"],  // Forbidden imports
      "require": []                  // Required imports (future)
    }
  }
}
```

### Managed Files

The `managed` section controls auto-generated files:

```jsonc
"managed": {
  "linters": {
    "ruff.toml": { "template": "linters/python/ruff.toml.template", "enabled": true }
  },
  "github": {
    ".github/workflows/release.yml": { "template": "github/workflows/release-python.yml.template", "enabled": true }
  },
  "docs": {
    "CLAUDE.md": { "type": "auto_sections", "enabled": true }
  },
  "ignore": {
    ".gitignore": { "template": ["gitignore/common.gitignore", "gitignore/python.gitignore"], "enabled": true }
  }
}
```

## Commands

All commands use the `/dk` prefix.

### Development

| Command | Description |
|---------|-------------|
| `/dk dev feat <desc>` | Develop new feature |
| `/dk dev fix <desc>` | Fix a bug |
| `/dk dev chore <desc>` | Maintenance task |
| `/dk dev refactor <desc>` | Code refactoring |
| `/dk dev test <desc>` | Add tests |

### Git Workflow

| Command | Description |
|---------|-------------|
| `/dk git init` | Initialize project (git, config, files, commit) |
| `/dk git update` | Sync managed files and GitHub settings |
| `/dk git pr` | Create pull request |
| `/dk git pr review [n]` | Check PR review status |
| `/dk git pr merge [n]` | Merge PR (squash) |
| `/dk git branch <name>` | Create feature branch |
| `/dk git squash` | Squash commits on branch |
| `/dk git cleanup` | Clean local tags + branches |

### Issues

| Command | Description |
|---------|-------------|
| `/dk git issue create` | Create issue in current project |
| `/dk git issue list` | List open issues |
| `/dk git issue view [n]` | View issue details |
| `/dk git issue report` | Report bug in devkit-plugin |

### Architecture

| Command | Description |
|---------|-------------|
| `/dk arch` | Architecture overview |
| `/dk arch analyze` | Analyze dependencies |
| `/dk arch check` | Check layer rule compliance |
| `/dk arch init [python\|ts]` | Scaffold Clean Architecture |
| `/dk arch layers` | Show layer documentation |

### Plugin Health

| Command | Description |
|---------|-------------|
| `/dk plugin check` | Run all health checks including consistency |
| `/dk plugin update` | Sync managed files and fix issues |

### Environment

| Command | Description |
|---------|-------------|
| `/dk env sync` | Sync .env to Vercel + GitHub |
| `/dk env pull` | Pull env vars from Vercel |
| `/dk env list` | List env vars |
| `/dk env clean` | Remove unused env vars |

### Deployment

| Command | Description |
|---------|-------------|
| `/dk vercel connect` | Link project to Vercel |
| `/dk vercel env` | Manage Vercel env vars |
| `/dk neon branch list` | List NeonDB branches |
| `/dk neon branch create` | Create NeonDB branch |
| `/dk neon branch delete` | Delete NeonDB branch |
| `/dk neon branch switch` | Switch NeonDB branch |
| `/dk neon cleanup` | Clean stale branches |

### Documentation

| Command | Description |
|---------|-------------|
| `/dk docs` | Show CLAUDE.md status |
| `/dk docs update` | Update AUTO sections |
| `/dk docs init` | Create CLAUDE.md from template |

## Hooks

Hooks are Claude Code event handlers that run automatically.

### SessionStart (session.py)

- Shows git status and branch info
- Loads project config

### PreToolUse (validate.py)

Validates commands before execution:
- Blocks `git push --force` on protected branches
- Blocks dangerous gh commands (`gh repo delete`, `gh secret delete`)
- Validates commit message format

### PostToolUse (format.py)

After file edits:
- Auto-formats Python files with ruff
- Auto-formats TypeScript/JavaScript with prettier
- Auto-formats Markdown with markdownlint

### ExitPlanMode (plan.py)

When leaving plan mode:
- Injects development workflow instructions
- Adds commit conventions reminder

## GitHub Workflows

### release.yml

Auto-release on push to main:
1. Generates changelog from commits
2. Bumps version based on commit types
3. Creates git tag
4. Publishes GitHub release

### claude-code-review.yml

AI code review on pull requests:
1. Triggers on PR open/update
2. Claude reviews changes
3. Updates PR body checkboxes
4. Posts review comments

### claude.yml

Claude assistant on issues/PRs:
- Responds to @claude mentions
- Answers questions about code



## Commit Conventions

**Format**: `type(scope): message`

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `chore` | Maintenance |
| `refactor` | Restructure |
| `test` | Tests |
| `perf` | Performance |
| `ci` | CI/CD |

### Internal Scopes

These scopes skip release notes:

| Scope | Use Case |
|-------|----------|
| `internal` | Internal refactoring |
| `review` | Code review fixes |
| `ci` | CI/CD changes |
| `deps` | Dependency updates |

### Changelog Formatting

Commits with scope become bold in changelog:
- `fix(auth): login crash` → **Auth**: Login crash
- `feat: new button` → New button

## Troubleshooting

### Config not found

```bash
# Check config exists
ls .claude/.devkit/config.jsonc

# Initialize if missing
/dk git init
```

### JSONC parse error

Check for:
- Trailing commas (not allowed in JSONC)
- Unclosed comments
- Invalid JSON syntax

### Force push blocked

Protected branches cannot be force pushed:
```bash
# Use revert instead
git revert HEAD
git push
```

### Auto-merge not working

Requirements:
1. Branch protection enabled
2. `github.pr.auto_merge: true` in config
3. All status checks must pass

### Linter not running

Check `hooks.format.enabled` is true in config.

## File Locations

| File | Purpose |
|------|---------|
| `.claude/.devkit/config.jsonc` | Plugin configuration |
| `.claude/.devkit/config.schema.json` | Config validation schema |
| `CLAUDE.md` | Project instructions for Claude |
| `docs/PLUGIN.md` | This documentation |
| `.github/workflows/` | GitHub Actions |
