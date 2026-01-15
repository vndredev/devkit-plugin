# /dk plugin

Plugin management, health check, and sync system.

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

⚠ Missing optional sections (3):
  - hooks.plan.planning
  - hooks.plan.implementation
  - hooks.plan.hints
  → Run: /dk plugin update (adds defaults)

── Sync ────────────────────────────
✓ ruff.toml (in sync)
✓ .gitignore (in sync)
✗ .markdownlint.json (outdated)
  → Run: /dk plugin update

── Architecture ────────────────────
✓ Layer rules compliant
  core (0) → lib (1) → arch (2) → events (3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: 1 issue found
Action: /dk plugin update
```

---

## /dk plugin update

Sync all managed files and upgrade config:

1. **Config upgrade:** Adds missing optional sections with defaults
2. **Linters:** ruff.toml, .markdownlint.json, etc.
3. **GitHub:** Workflows and issue templates
4. **Docs:** CLAUDE.md, docs/PLUGIN.md
5. **Ignore:** .gitignore, etc.

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.sync import sync_all

print('=== Syncing Plugin Files ===')
print()
results = sync_all()
for target, success, msg in results:
    icon = '✓' if success else '✗'
    print(f'{icon} {target}')
print()
print('Done!')
"
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
        '.github/ISSUE_TEMPLATE/config.yml': { 'template': 'github/ISSUE_TEMPLATE/config.yml.template', 'enabled': True }
    },
    'docs': {
        'CLAUDE.md': { 'type': 'auto_sections', 'enabled': True },
        'docs/PLUGIN.md': { 'type': 'auto_generate', 'enabled': True }
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

## Notes

- All generated files are based on templates in the plugin's `templates/` directory
- CLAUDE.md preserves `<!-- CUSTOM:name -->` sections during updates
- Health check runs automatically at session start (compact warning)
- Use `/dk plugin check` for detailed report
- Use `/dk plugin update` to fix sync issues
