# /dk docs - Auto Documentation

Manage CLAUDE.md with AUTO-generated and CUSTOM sections.

## Commands

| Command | Description |
|---------|-------------|
| `/dk docs` | Show current CLAUDE.md status |
| `/dk docs update` | Update AUTO sections from config |
| `/dk docs init` | Create CLAUDE.md from template |

## Section Types

### AUTO Sections

Generated from config.json - **DO NOT EDIT MANUALLY**:

```markdown
<!-- AUTO:START -->
## Commands
...generated from skills...

## Architecture
...generated from config...

## Tech Stack
...detected from project...
<!-- AUTO:END -->
```

### CUSTOM Sections

User/Claude maintained - preserved during updates:

```markdown
<!-- CUSTOM:START -->
## Project Specific
...your documentation...
<!-- CUSTOM:END -->
```

## Workflow

### /dk docs

Show CLAUDE.md status:

```bash
# Check if CLAUDE.md exists and show section status
if [ -f "CLAUDE.md" ]; then
    echo "CLAUDE.md exists"
    grep -c "AUTO:START" CLAUDE.md && echo "Has AUTO section"
    grep -c "CUSTOM:START" CLAUDE.md && echo "Has CUSTOM section"
else
    echo "CLAUDE.md not found - run /dk docs init"
fi
```

### /dk docs update

Update only the AUTO sections:

1. Read current CLAUDE.md
2. Extract CUSTOM sections (preserve them)
3. Regenerate AUTO sections from config
4. Merge: new AUTO + preserved CUSTOM
5. Write updated CLAUDE.md

```python
# Pseudo-code
def update_docs():
    content = read_file("CLAUDE.md")
    custom_sections = extract_between(content, "CUSTOM:START", "CUSTOM:END")

    auto_content = generate_auto_sections()

    new_content = f"""# {project_name}

{auto_content}

{custom_sections}
"""
    write_file("CLAUDE.md", new_content)
```

### /dk docs init

Create CLAUDE.md from template:

```python
# Use template from ${PLUGIN_ROOT}/templates/CLAUDE.md.template
# Replace placeholders with config values
# Preserve any existing CUSTOM sections
```

## AUTO Section Generation

### Commands Section

Generated from skills/dk/SKILL.md command table:

```markdown
## Commands

| Command | Description |
|---------|-------------|
| `/dk` | Show status and available commands |
| `/dk dev feat <desc>` | Develop new feature |
...
```

### Architecture Section

Generated from config.json arch settings:

```markdown
## Architecture

- **Type:** python
- **Layers:** 4 (core, lib, arch, events)
- **Pattern:** Clean Architecture
```

### Tech Stack Section

Auto-detected from project files:

```markdown
## Tech Stack

- **Language:** Python 3.10+
- **Runtime:** Claude Code Hooks
- **Package Manager:** uv
- **Linters:** ruff, markdownlint
```

## Key Rules

1. **NEVER edit AUTO sections manually** - they get overwritten
2. **ALWAYS put custom docs in CUSTOM sections** - they're preserved
3. **Run /dk docs update after config changes** - keeps docs in sync
4. **Use /dk docs init for new projects** - creates proper structure
