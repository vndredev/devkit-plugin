# /dk env

Environment variable sync for Vercel + GitHub.

## Commands

| Command | Description |
|---------|-------------|
| `/dk env sync` | Sync env files to Vercel + GitHub |
| `/dk env pull` | Pull env vars from Vercel |
| `/dk env list` | List current env vars |
| `/dk env clean` | Remove unused env vars |

---

## Environment Files

| File | Purpose | Synced to | Git |
|------|---------|-----------|-----|
| `.env` | Shared defaults | - | ✅ commit |
| `.env.production` | Production | Vercel Production + GitHub | ❌ gitignore |
| `.env.preview` | Preview | Vercel Preview | ❌ gitignore |
| `.env.development` | Development | Vercel Development | ❌ gitignore |
| `.env.local` | Local overrides | Not synced | ❌ gitignore |

---

## /dk env sync

Sync environment variables based on project type:

1. Check project type from `.claude/.devkit/config.json`
2. Sync `.env.production` → GitHub Secrets
3. If nextjs/node: Sync to Vercel environments

```bash
# Parse env file and sync to GitHub
while IFS= read -r line; do
    key="${line%%=*}"
    value="${line#*=}"
    gh secret set "$key" --body "$value"
done < .env.production

# Sync to Vercel (nextjs/node only)
vercel env add "$key" production --force
```

---

## /dk env pull

Pull env vars from Vercel (restore after clone):

```bash
vercel env pull .env.production --environment=production --yes
vercel env pull .env.preview --environment=preview --yes
vercel env pull .env.development --environment=development --yes
```

---

## /dk env list

List current env vars:

```bash
echo "=== Vercel ==="
vercel env ls production
vercel env ls preview
vercel env ls development

echo "=== GitHub Secrets ==="
gh secret list

echo "=== Local Files ==="
ls -la .env*
```

---

## /dk env clean

Remove env vars NOT in source files:

1. Safety check: require at least one `.env.*` file
2. Extract keys from each env file
3. Compare with Vercel/GitHub
4. Delete vars not in source files

---

## Project Type Matrix

| Type | Vercel | GitHub | Notes |
|------|--------|--------|-------|
| `nextjs` | ✅ | ✅ | Full sync |
| `node` | ✅ | ✅ | Full sync |
| `python` | ❌ | ✅ | No Vercel |
| `plugin` | ❌ | ✅ | No Vercel |

---

## DATABASE_URL Handling

When using Neon-Vercel integration, `DATABASE_URL` is managed automatically:

| Environment | Branch | Set by |
|-------------|--------|--------|
| Production | `main` | Neon-Vercel Integration |
| Preview | `preview/<branch>` | Auto per PR |
| Development | `vercel-dev` | Neon-Vercel Integration |

**Do NOT include DATABASE_URL in `.env.production`** when using Neon-Vercel integration.

---

## Prerequisites

- `gh` CLI: `brew install gh && gh auth login`
- `vercel` CLI: `npm i -g vercel && vercel login`
