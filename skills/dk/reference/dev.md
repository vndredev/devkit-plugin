# /dk dev

**CRITICAL:** Development workflow commands. YOU MUST use these for ALL code changes.

## Commands

| Command                   | Type     | Description |
| ------------------------- | -------- | ----------- |
| `/dk dev feat <desc>`     | feat     | New feature |
| `/dk dev fix <desc>`      | fix      | Bug fix     |
| `/dk dev chore <desc>`    | chore    | Maintenance |
| `/dk dev refactor <desc>` | refactor | Restructure |
| `/dk dev test <desc>`     | test     | Add tests   |

---

## Workflow

**YOU MUST follow this workflow for ALL code changes:**

1. **Explore** - YOU MUST understand context first (Explore agent)
2. **Plan** - YOU MUST design approach (Plan agent for feat/refactor)
3. **Build** - Implement + test + commit

---

## Rules (MANDATORY)

**YOU MUST follow these rules - NO EXCEPTIONS:**

- **ALWAYS** read `CLAUDE.md` before coding
- **ALWAYS** use `TodoWrite` to track progress
- **ALWAYS** commit after each logical unit
- **NEVER** create PRs with >20 files or >500 lines

---

## Commit Format

**YOU MUST use Conventional Commits**: `type(scope): message`

```bash
git commit -m "type(scope): description

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**ALLOWED types:** `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `ci`

**Scope is optional** but if used, must be from allowed list in config.

**NEVER** use other commit types. **NEVER** skip the Co-Authored-By line.

---

## Documentation Resources

**ALWAYS use these resources:**

- Claude Code questions → **ALWAYS** use `claude-code-guide` agent
- Library docs → **ALWAYS** use Context7 MCP tools

---

## Consistency Checkliste

**After creating new files, verify these artifacts exist:**

- [ ] **Tests**: New modules in `src/` need test files in `tests/test_{module}.py`
- [ ] **Handlers**: Enabled hooks need handler files in `src/events/`
- [ ] **Docs**: New skills need reference docs in `skills/dk/reference/`

**Run `/dk plugin check` to verify all consistency rules.**

---

## IMPORTANT Reminders

1. **NEVER** use raw `gh pr create` - **ALWAYS** use `/dk git pr`
2. **NEVER** skip tests - **ALWAYS** run `uv run pytest` before committing
3. **NEVER** skip linting - **ALWAYS** run `uv run ruff check` after changes
4. **ALWAYS** run `/dk plugin check` before creating a PR
