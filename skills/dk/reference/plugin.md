# /dk plugin

**CRITICAL:** Plugin management, health check, and sync system.

**YOU MUST run `/dk plugin check` when issues are detected.**

## Commands

| Command             | Action                                      |
| ------------------- | ------------------------------------------- |
| `/dk plugin`        | Quick status                                |
| `/dk plugin check`  | Full health check with content verification |
| `/dk plugin update` | Sync all managed files                      |
| `/dk plugin init`   | Initialize new project                      |

---

## /dk plugin - Quick Status

Show project info and quick health summary.

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.config import get
from arch.check import check_all

print('=== Project ===')
print(f'Name: {get(\"project.name\", \"unknown\")}')
print(f'Type: {get(\"project.type\", \"unknown\")}')
print()

print('=== Linters ===')
linters = get('linters', {})
print(f'Preset: {linters.get(\"preset\", \"strict\")}')
print()

# Quick health status
results = check_all()
if results['healthy']:
    print('✓ Plugin healthy')
else:
    issue_count = len(results['config']['errors']) + len(results['sync']['issues']) + len(results['arch']['violations'])
    print(f'⚠️ {issue_count} issue(s) - run /dk plugin check')
"
```

---

## /dk plugin check

Full health check with content verification:

- **Config:** Schema validation, required fields, missing optional sections
- **Sync:** Content comparison against templates
- **Architecture:** Layer rule compliance
- **Consistency:** Module tests, hook handlers, skill routes, custom imports
- **Upgradable:** Detects if config can be upgraded with new features

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from arch.check import check_all, format_report

results = check_all()
print(format_report(results))
"
```

### Output Example

```
── Config ──────────────────────────
✓ Schema valid
✓ Required fields present

── Sync ────────────────────────────
✓ ruff.toml (in sync)
✓ .gitignore (in sync)
✗ .markdownlint.json (outdated)
  → Run: /dk plugin update

── Architecture ────────────────────
✓ Layer rules compliant
  core (0) → lib (1) → arch (2) → events (3)

── Consistency ─────────────────────
✓ All consistency checks passed
  OR
✗ 2 consistency violation(s):
  ⚠️ [module_tests] Missing test file for tools.py
  ❌ [hook_handlers] Hook references missing handler

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: 1 issue found
Action: /dk plugin update
```

---

## /dk plugin update

Sync all managed files, upgrade config, and install user files:

1. **Plugin update:** Checks GitHub for new version, clears cache if update available
2. **Versions:** Syncs version across package.json, config.jsonc, pyproject.toml
3. **Config upgrade:** Adds missing optional sections with defaults
4. **Linters:** ruff.toml, .markdownlint.json, etc.
5. **GitHub:** Workflows and issue templates
6. **Docs:** CLAUDE.md, docs/PLUGIN.md
7. **Ignore:** .gitignore, etc.
8. **User files:** ~/.claude/statusline.sh (Claude Code status line)

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.sync import sync_all, install_user_files, format_sync_report

results = sync_all()
user_results = install_user_files()
print(format_sync_report(results, user_results))
"
```

### Auto-Update Behavior

When a new plugin version is available on GitHub:

1. **Detection:** Compares cached version with latest GitHub release
2. **Cache clear:** Removes `~/.claude/plugins/cache/vndredev-marketplace/devkit-plugin/`
3. **User action:** Restart Claude Code session to load new version

Example output when update is available:

```
✓ plugin update: 0.23.2 → 0.24.0
✓ cache cleared: Restart session to load new version
```

---

## /dk plugin init

Initialize a new project with devkit-plugin configuration.

**Steps:**

1. Detect project type (python, nextjs, typescript, javascript)
2. Create `.claude/.devkit/config.jsonc` with `managed` section
3. Run `/dk plugin update` to generate all files

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.tools import detect_project_type
from lib.config import get_project_root
from pathlib import Path
import json

root = get_project_root()
project_type = detect_project_type(root)
project_name = root.name

print(f'Detected project type: {project_type.value}')
print(f'Project name: {project_name}')

config_dir = root / '.claude' / '.devkit'
config_dir.mkdir(parents=True, exist_ok=True)

# Build managed section based on project type
managed = {
    'linters': {
        '.markdownlint.json': { 'template': 'linters/common/markdownlint.json.template', 'enabled': True },
        '.markdownlintignore': { 'template': 'gitignore/markdownlint.ignore', 'enabled': True }
    },
    'github': {
        '.github/workflows/claude.yml': { 'template': 'github/workflows/claude.yml.template', 'enabled': True },
        '.github/workflows/claude-code-review.yml': { 'template': 'github/workflows/claude-code-review.yml.template', 'enabled': True },
        '.github/ISSUE_TEMPLATE/bug_report.yml': { 'template': 'github/ISSUE_TEMPLATE/bug_report.yml.template', 'enabled': True },
        '.github/ISSUE_TEMPLATE/feature_request.yml': { 'template': 'github/ISSUE_TEMPLATE/feature_request.yml.template', 'enabled': True },
        '.github/ISSUE_TEMPLATE/config.yml': { 'template': 'github/ISSUE_TEMPLATE/config.yml.template', 'enabled': True },
        '.github/PULL_REQUEST_TEMPLATE.md': { 'template': 'github/PULL_REQUEST_TEMPLATE.md.template', 'enabled': True }
    },
    'docs': {
        'README.md': { 'type': 'auto_sections', 'enabled': True },
        'CLAUDE.md': { 'type': 'auto_sections', 'enabled': True },
        'docs/PLUGIN.md': { 'type': 'template', 'template': 'docs/PLUGIN.md.template', 'enabled': True }
    },
    'ignore': {}
}

# Project-type specific files
if project_type.value == 'python':
    managed['linters']['ruff.toml'] = { 'template': 'linters/python/ruff.toml.template', 'enabled': True }
    managed['github']['.github/workflows/release.yml'] = { 'template': 'github/workflows/release-python.yml.template', 'enabled': True }
    managed['ignore']['.gitignore'] = { 'template': ['gitignore/common.gitignore', 'gitignore/python.gitignore'], 'enabled': True }
elif project_type.value in ('nextjs', 'typescript', 'javascript'):
    managed['linters']['.eslintrc.json'] = { 'template': 'linters/nextjs/eslint.json.template', 'enabled': True }
    managed['linters']['.prettierrc'] = { 'template': 'linters/nextjs/prettier.json.template', 'enabled': True }
    managed['linters']['.prettierignore'] = { 'template': 'gitignore/prettier.ignore', 'enabled': True }
    managed['github']['.github/workflows/release.yml'] = { 'template': 'github/workflows/release-node.yml.template', 'enabled': True }
    managed['ignore']['.gitignore'] = { 'template': ['gitignore/common.gitignore', 'gitignore/nextjs.gitignore'], 'enabled': True }

config = {
    '\$schema': './config.schema.json',
    'project': {
        'name': project_name,
        'type': project_type.value
    },
    'hooks': {
        'session': { 'enabled': True, 'show_git_status': True },
        'validate': { 'enabled': True, 'block_force_push': True },
        'format': { 'enabled': True, 'auto_format': True },
        'plan': { 'enabled': True }
    },
    'git': {
        'protected_branches': ['main']
    },
    'github': {
        'url': f'https://github.com/owner/{project_name}'
    },
    'arch': {
        'layers': {}
    },
    'linters': {
        'preset': 'strict',
        'overrides': {}
    },
    'managed': managed
}

config_file = config_dir / 'config.jsonc'
config_file.write_text(json.dumps(config, indent=2))
print(f'Created: {config_file}')
print()
print('Run /dk plugin update to generate all files.')
"
```

---

## Config Structure

The `config.jsonc` is the single source of truth:

```json
{
  "project": { "name": "...", "type": "python|nextjs|..." },
  "linters": { "preset": "strict|relaxed|minimal", "overrides": {} },
  "arch": { "layers": { "core": { "tier": 0 }, ... } },
  "consistency": {
    "enabled": true,
    "rules": {
      "module_tests": { "enabled": true, "patterns": {...}, "exclude": [...] },
      "hook_handlers": { "enabled": true },
      "config_schema": { "enabled": true },
      "skill_routes": { "enabled": true },
      "custom_imports": { "enabled": false, "deny": [...] }
    }
  },
  "managed": {
    "linters": { "ruff.toml": { "template": "...", "enabled": true } },
    "github": { ".github/workflows/...": { "template": "...", "enabled": true } },
    "docs": { "CLAUDE.md": { "type": "auto_sections", "enabled": true } },
    "ignore": { ".gitignore": { "template": ["...", "..."], "enabled": true } }
  }
}
```

### Managed Section

| Category  | Description                                           |
| --------- | ----------------------------------------------------- |
| `linters` | Linter config files (ruff.toml, .eslintrc.json, etc.) |
| `github`  | GitHub workflows and issue templates                  |
| `docs`    | Documentation files (CLAUDE.md, PLUGIN.md)            |
| `ignore`  | Ignore files (.gitignore, .prettierignore, etc.)      |

### Disabling Files

Set `enabled: false` to skip a managed file:

```json
{
  "managed": {
    "linters": {
      "ruff.toml": { "template": "...", "enabled": false }
    }
  }
}
```

---

## Notes (IMPORTANT)

- All generated files are based on templates in the plugin's `templates/` directory
- CLAUDE.md preserves `<!-- CUSTOM:name -->` sections during updates
- Health check runs automatically at session start (compact warning)
- **YOU MUST use `/dk plugin check`** for detailed report when issues occur
- **YOU MUST use `/dk plugin update`** to fix sync issues - NEVER edit generated files manually

---

## Marketplace Management

The marketplace (`~/dev/claude-marketplace`) has two layers:

| Layer             | File               | Synced to GitHub  |
| ----------------- | ------------------ | ----------------- |
| **Prod** (public) | `marketplace.json` | ✓ Yes             |
| **Dev** (local)   | `local.json`       | ✗ No (gitignored) |

### /dk plugin marketplace

Show marketplace status:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
import json
from pathlib import Path

marketplace_dir = Path.home() / 'dev' / 'claude-marketplace'
manifest = marketplace_dir / '.claude-plugin' / 'marketplace.json'
local = marketplace_dir / '.claude-plugin' / 'local.json'

if not manifest.exists():
    print('❌ Marketplace not found')
else:
    data = json.loads(manifest.read_text())
    local_data = json.loads(local.read_text()) if local.exists() else {}

    print(f'Marketplace: {data[\"name\"]}')
    print()
    for plugin in data.get('plugins', []):
        name = plugin['name']
        dev_override = local_data.get(name, {}).get('source')
        print(f'  {name}:')
        print(f'    prod: v{plugin.get(\"version\", \"?\")}')
        if dev_override:
            print(f'    dev:  {dev_override}')
"
```

### /dk plugin marketplace sync

Sync prod marketplace to GitHub:

```bash
cd ~/dev/claude-marketplace && git add -A && git status --short
```

If changes exist, commit and push:

```bash
cd ~/dev/claude-marketplace && git commit -m "chore: update marketplace" && git push
```

### /dk plugin publish

Update prod version in marketplace (after `git tag vX.Y.Z`):

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
import json
from pathlib import Path
from lib.version import get_version

version = get_version()
print(f'Publishing version: {version}')

marketplace = Path.home() / 'dev' / 'claude-marketplace' / '.claude-plugin' / 'marketplace.json'
data = json.loads(marketplace.read_text())

for plugin in data.get('plugins', []):
    if plugin['name'] == 'devkit-plugin':
        plugin['version'] = version
        break

marketplace.write_text(json.dumps(data, indent=2) + '\n')
print(f'✓ Updated marketplace.json')
print()
print('Next: /dk plugin marketplace sync')
"
```

### /dk plugin dev

Setup local dev override (local.json, gitignored):

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
import json
from pathlib import Path

plugin_dir = Path.cwd()
local_file = Path.home() / 'dev' / 'claude-marketplace' / '.claude-plugin' / 'local.json'

data = json.loads(local_file.read_text()) if local_file.exists() else {}
data['devkit-plugin'] = {'source': str(plugin_dir)}

local_file.write_text(json.dumps(data, indent=2) + '\n')
print(f'✓ Dev override: {plugin_dir}')
print('  (local.json is gitignored)')
"
```
