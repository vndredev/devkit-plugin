# /dk dev

Development workflow commands.

## Commands

| Command | Type | Description |
|---------|------|-------------|
| `/dk dev feat <desc>` | feat | New feature |
| `/dk dev fix <desc>` | fix | Bug fix |
| `/dk dev chore <desc>` | chore | Maintenance |
| `/dk dev refactor <desc>` | refactor | Restructure |
| `/dk dev test <desc>` | test | Add tests |

---

## Workflow

1. **Explore** - Understand context first (Explore agent)
2. **Plan** - Design approach (Plan agent for feat/refactor)
3. **Build** - Implement + test + commit

---

## Rules

- Read `CLAUDE.md` before coding
- Use `TodoWrite` to track progress
- Commit after each logical unit
- Keep PRs small (<20 files, <500 lines)

---

## Commit Format

```bash
git commit -m "<type>: <description>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`
