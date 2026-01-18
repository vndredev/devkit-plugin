# /dk neon

**CRITICAL:** NeonDB branch management for local development.

**YOU MUST use `/dk neon` commands for database branch operations.**

## Branch Architecture

The Neon-Vercel integration creates these branches automatically:

| Branch             | Type        | Created by               | Purpose                   |
| ------------------ | ----------- | ------------------------ | ------------------------- |
| `main`             | Production  | Default                  | Live production data      |
| `vercel-dev`       | Development | Vercel Integration       | Local `vercel dev`        |
| `preview/<branch>` | Preview     | Auto per PR              | Preview deployments       |
| `dev-<user>`       | Personal    | `/dk neon branch create` | Alternative to vercel-dev |

> **Recommended**: Use `vercel dev` which connects to `vercel-dev` branch automatically.
> Only use `/dk neon branch create` if you need isolated personal branches.

## Commands

| Command                         | Description                          |
| ------------------------------- | ------------------------------------ |
| `/dk neon branch create [name]` | Create personal dev branch           |
| `/dk neon branch delete <name>` | Delete database branch               |
| `/dk neon branch list`          | List all branches                    |
| `/dk neon branch switch <name>` | Switch to branch (update .env.local) |
| `/dk neon cleanup`              | Delete stale dev branches            |

## /dk neon branch create

Create a personal dev branch (alternative to `vercel-dev`):

```bash
BRANCH_NAME="${1:-dev-$(whoami)}"
```

First, get the project ID:

```
mcp__neon__list_projects → extract projectId from first result
```

Then create branch:

```
mcp__neon__create_branch with params:
  projectId: (from list_projects result)
  branchName: $BRANCH_NAME
```

Then get connection string:

```
mcp__neon__get_connection_string with params:
  projectId: (from list_projects result)
  branchId: (from create_branch result)
```

After creation:

1. Output branch name and connection string
2. **Ask user** if they want to add to `.env.local`
3. If yes, append `DATABASE_URL` to `.env.local`

> **Note**: Personal branches are useful when multiple developers need isolated databases. For solo development, `vercel dev` with `vercel-dev` branch is simpler.

## /dk neon branch delete

Delete a NeonDB branch:

```bash
BRANCH_NAME="${1}"
if [ -z "$BRANCH_NAME" ]; then
  echo "Usage: /dk neon branch delete <branch-name>"
  exit 1
fi
```

Use MCP tools:

```
mcp__neon__list_projects → extract projectId
mcp__neon__describe_project → find branchId by name
mcp__neon__delete_branch with params:
  projectId: (from list_projects)
  branchId: (from describe_project, matching $BRANCH_NAME)
```

## /dk neon branch list

List all branches in the project:

```
mcp__neon__list_projects → get project ID
mcp__neon__describe_project → list branches
```

Output table with branch types:

| Branch             | Type        | Created    | Notes                  |
| ------------------ | ----------- | ---------- | ---------------------- |
| main               | Production  | 2024-01-01 | Default branch         |
| vercel-dev         | Development | 2024-01-10 | For `vercel dev`       |
| preview/feat/login | Preview     | 2024-01-12 | Auto-created by Vercel |
| dev-andre          | Personal    | 2024-01-10 | Manual dev branch      |

Branch type detection:

- `main` → Production
- `vercel-dev` → Development
- `preview/*` → Preview (Vercel auto-created)
- `dev-*` → Personal development

## /dk neon branch switch

Switch local development to a different branch:

```bash
BRANCH_NAME="${1}"
```

1. Get connection string for branch
2. Update `DATABASE_URL` in `.env.local`
3. Confirm switch

## /dk neon cleanup

Delete stale development branches (older than 7 days, not main):

```bash
echo "Checking for stale dev branches..."

# List all dev-* branches older than 7 days
# Exclude: main, preview-* (managed by Vercel)
```

Use MCP tools to:

1. List branches matching `dev-*` pattern
2. Check creation date
3. Delete branches older than 7 days (with confirmation)

## Environment Variables

For local development, add to `.env.local`:

```bash
DATABASE_URL="postgres://user:pass@host/db?sslmode=require"
```

## Prerequisites

- NeonDB account with project
- `neonctl` CLI installed: `npm i -g neonctl`
- Authenticated: `neonctl auth`
- NeonDB MCP server configured (for MCP tools)

## Best Practices

1. **One dev branch per developer** - Use `dev-$(whoami)` naming
2. **Never use main for development** - Main = Production
3. **Clean up regularly** - Run `/dk neon cleanup` weekly
4. **Use native integration for previews** - Vercel Dashboard → Integrations → Neon
