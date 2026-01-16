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

**YOU MUST use this exact format for ALL commits:**

```bash
git commit -m "<type>: <description>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**ALLOWED types:** `feat`, `fix`, `chore`, `refactor`, `test`, `docs`

**NEVER** use other commit types. **NEVER** skip the Co-Authored-By line.

---

## Documentation Resources

**ALWAYS use these resources:**

- Claude Code questions → **ALWAYS** use `claude-code-guide` agent
- Library docs → **ALWAYS** use Context7 MCP tools

---

## IMPORTANT Reminders

1. **NEVER** use raw `gh pr create` - **ALWAYS** use `/dk git pr`
2. **NEVER** skip tests - **ALWAYS** run `uv run pytest` before committing
3. **NEVER** skip linting - **ALWAYS** run `uv run ruff check` after changes
