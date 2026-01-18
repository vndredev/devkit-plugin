# /dk arch - Architecture Analysis

**CRITICAL:** Clean Architecture analysis, validation, and scaffolding.

**YOU MUST respect layer boundaries at ALL times.**

## When to Use /dk arch vs /dk dev

| Scenario                       | Use                        |
| ------------------------------ | -------------------------- |
| Analyze/check architecture     | `/dk arch analyze\|check`  |
| Find similar code before write | `/dk arch discover <name>` |
| Scaffold new project structure | `/dk arch init` (on main)  |
| Writing code in layers         | `/dk dev feat\|fix <desc>` |

**Note:** `/dk arch init` scaffolds structure - use on `main` then branch for code.

## Commands

| Command                      | Description                                |
| ---------------------------- | ------------------------------------------ |
| `/dk arch`                   | Show architecture overview                 |
| `/dk arch analyze`           | Analyze dependencies and detect violations |
| `/dk arch check`             | Check layer rule compliance                |
| `/dk arch discover <name>`   | Find similar code before writing           |
| `/dk arch init [python\|ts]` | Scaffold Clean Architecture structure      |
| `/dk arch layers`            | Show layer documentation                   |

## Architecture Layers

```
TIER 4: Entry Points (entry/, hooks/)
   ↓ imports from
TIER 3: Usecases (usecases/)
   ↓ imports from
TIER 2: Adapters (adapters/)
   ↓ imports from
TIER 1: Domain (domain/)
   ↓ imports from
TIER 0: Core (core/)
```

## Import Rules

| Layer             | May Import From        |
| ----------------- | ---------------------- |
| core (TIER 0)     | Python stdlib only     |
| domain (TIER 1)   | core                   |
| adapters (TIER 2) | core, domain           |
| usecases (TIER 3) | core, domain, adapters |
| entry (TIER 4)    | All layers             |

## Workflow

### /dk arch

Show current architecture status:

```
# Architecture Overview

Project Type: python
Structure: Clean Architecture (4-tier)

Layers:
- core/: 5 files (types, errors, constants)
- domain/: 4 files (validation, detection)
- adapters/: 6 files (git, config, linters)
- usecases/: 2 files (session, file_processing)
- entry/: 4 files (hook handlers)

Status: ✅ No violations
```

### /dk arch analyze

Analyze dependencies and show graph:

```python
# Run analysis
from arch.analyze import analyze_dependencies, format_analysis_report
from lib.config import get_project_root

root = get_project_root()
analysis = analyze_dependencies(root)
print(format_analysis_report(analysis))
```

Output includes:

- Project type detection
- Dependency graph (file → imports)
- Layer distribution statistics
- Violation list (if any)

### /dk arch check

Quick compliance check:

```python
from arch.rules import check_layer_rules
from lib.config import get_project_root

success, message = check_layer_rules(get_project_root())
print(message)
```

Returns:

- ✅ if all imports follow rules
- ❌ with violation details if not

### /dk arch discover <name>

Find similar code before writing new functions/classes:

```python
from arch.discovery import find_duplicates_for_name, format_matches_report

# Search for similar function names
matches = find_duplicates_for_name("extract_imports", code_type="function")
print(format_matches_report(matches, context="for 'extract_imports'"))
```

Output:

```
Similar code found for 'extract_imports':

  [100%] src/arch/analyze.py:131
       def extract_imports_from_content(content: str) -> list[str]

  [80%] src/arch/analyze.py:165
       def extract_python_imports(file_path: Path) -> list[str]
```

**IMPORTANT:** Before writing new code, ALWAYS run `/dk arch discover <name>` to check
if similar functionality already exists. This prevents code duplication.

### /dk arch init [python|ts]

Scaffold Clean Architecture structure:

```python
from arch.rules import init_project, get_init_preview
from core.types import ProjectType
from lib.config import get_project_root

# Preview first
print(get_init_preview(ProjectType.PYTHON))

# Then create
created = init_project(get_project_root(), ProjectType.PYTHON)
for f in created:
    print(f"Created: {f}")
```

Creates:

- `src/core/` - types.py, errors.py
- `src/domain/` - validation.py
- `src/adapters/` - repository.py
- `src/usecases/` - create_entity.py
- `tests/` - test_domain.py

### /dk arch layers

Show layer documentation:

```python
from arch.rules import get_layer_info
print(get_layer_info())
```

## Best Practices (MANDATORY)

**YOU MUST follow these practices:**

1. **ALWAYS keep core pure** - No I/O, no external dependencies
2. **NEVER add side effects to domain** - Pure functions only
3. **ALWAYS wrap externals in adapters** - One adapter per external system
4. **Usecases orchestrate** - Combine domain + adapters
5. **ALWAYS keep entry points thin** - Just parse input and call usecases

## Violation Examples

❌ **Bad**: Domain importing from adapters

```python
# domain/validation.py
from adapters.config import load_config  # VIOLATION!
```

✅ **Good**: Usecase coordinates both

```python
# usecases/validate_flow.py
from domain.validation import validate
from adapters.config import load_config

def validate_with_config():
    config = load_config()
    return validate(config["rules"])
```
