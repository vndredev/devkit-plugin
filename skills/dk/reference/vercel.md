# /dk vercel

**CRITICAL:** Vercel deployment setup and management.

**YOU MUST use `/dk vercel` commands - NEVER use raw `vercel` CLI directly.**

## Commands

| Command                    | Description                                 |
| -------------------------- | ------------------------------------------- |
| `/dk vercel connect`       | Full Vercel setup (link, GitHub, env, Neon) |
| `/dk vercel status`        | Show current Vercel project status          |
| `/dk vercel deploy`        | Deploy to preview                           |
| `/dk vercel deploy --prod` | Deploy to production                        |
| `/dk vercel env sync`      | Sync .env.local to Vercel                   |
| `/dk vercel env pull`      | Pull env vars from Vercel                   |

---

## /dk vercel connect

Full automated Vercel setup:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.vercel import vercel_connect
for step, ok, msg in vercel_connect():
    icon = '✓' if ok else '✗'
    print(f'{icon} {step}: {msg}')
"
```

**Workflow:**

1. Check Vercel CLI installed & authenticated
2. Link project (or create new)
3. **Connect GitHub** (auto-connects if not connected)
4. Check production domain
5. Sync environment variables from `.env.local`
6. Check Neon integration (if DATABASE_URL exists)

**Output Example:**

```
✓ vercel cli: 50.1.3 (logged in as dfineio)
✓ vercel link: Already linked to dfine-streaming
✓ project info: dfine-streaming @ dfineio
✓ github integration: Connected to vndredev/dfine-streaming
✓ production domain: streaming.dfine.app
✓ env sync: All vars already synced
✓ neon integration: Neon integration active (per-branch DB)
```

---

## /dk vercel status

Show current project status:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.vercel import vercel_status
import json
status = vercel_status()
print(json.dumps(status, indent=2))
"
```

---

## /dk vercel deploy

Deploy to Vercel:

```bash
# Preview deployment
vercel deploy

# Production deployment
vercel deploy --prod
```

---

## /dk vercel env sync

Sync environment variables from `.env.local` to Vercel:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.vercel import sync_env_vars
from pathlib import Path
for step, ok, msg in sync_env_vars(Path.cwd()):
    icon = '✓' if ok else '✗'
    print(f'{icon} {step}: {msg}')
"
```

**Security:** Sensitive vars are skipped automatically:

- Variables containing `SECRET`, `KEY`, `TOKEN`, `PASSWORD`, `PRIVATE`
- These must be added manually via `vercel env add`

---

## /dk vercel env pull

Pull environment variables from Vercel to local:

```bash
vercel env pull .env.local
```

---

## Prerequisites

| Tool          | Install           | Check              |
| ------------- | ----------------- | ------------------ |
| Vercel CLI    | `npm i -g vercel` | `vercel --version` |
| Authenticated | `vercel login`    | `vercel whoami`    |

---

## Integration with GitHub

After `/dk vercel connect`:

- Push to `main` → Production deployment
- Push to feature branch → Preview deployment
- PR created → Preview URL in PR comments

**Setup GitHub Integration:**

1. Go to Vercel Dashboard → Project → Settings → Git
2. Connect repository
3. Enable "Auto-deploy on push"

---

## Integration with NeonDB

For automatic database branches per preview deployment:

1. Go to Vercel Dashboard → Integrations → Neon
2. Connect your Neon project
3. Enable "Create branch per preview"

**Benefits:**

- Creates DB branch per Vercel preview deployment
- Sets `DATABASE_URL` automatically per environment
- Cleans up branches when deployments are deleted

---

## Project Structure

After `/dk vercel connect`:

```
.vercel/
├── project.json    # Project ID & Org ID
└── README.txt      # Vercel info
```

---

## Troubleshooting

| Issue               | Solution              |
| ------------------- | --------------------- |
| "Not logged in"     | `vercel login`        |
| "Project not found" | `vercel link`         |
| "Permission denied" | Check team membership |
| "Build failed"      | Check `vercel logs`   |
