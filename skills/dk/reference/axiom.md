# /dk axiom

**CRITICAL:** Axiom logging/observability management via CLI.

## Prerequisites

- Axiom CLI installed: `brew install axiom`
- Authenticated: `axiom auth login`

## Commands

| Command                            | Description           |
| ---------------------------------- | --------------------- |
| `/dk axiom`                        | Show status + auth    |
| `/dk axiom login`                  | Authenticate          |
| `/dk axiom datasets`               | List datasets         |
| `/dk axiom datasets create <name>` | Create dataset        |
| `/dk axiom datasets delete <name>` | Delete dataset        |
| `/dk axiom query "<apl>"`          | Execute APL query     |
| `/dk axiom stream <dataset>`       | Livestream logs       |
| `/dk axiom ingest <dataset>`       | Ingest data           |
| `/dk axiom web`                    | Open dashboard        |
| `/dk axiom test`                   | Test connectivity     |
| `/dk axiom token`                  | Show token info       |
| `/dk axiom token create`           | Guide to create token |
| `/dk axiom token test`             | Validate token        |

---

## /dk axiom

Show Axiom status (CLI, auth, token, datasets):

```bash
uv run python -c "
from lib.axiom import axiom_status
import json
status = axiom_status()
print('CLI:', 'OK' if status['cli_installed'] else 'Not installed')
print('Auth:', 'OK' if status['authenticated'] else 'Not authenticated')
print('Token:', status['token']['masked_token'] or 'Not set')
print('Datasets:', status['dataset_count'])
print('Dashboard:', status['dashboard'])
"
```

---

## /dk axiom login

Authenticate with Axiom (interactive):

```bash
axiom auth login
```

After login, verify:

```bash
axiom auth status
```

---

## /dk axiom datasets

List all datasets:

```bash
axiom dataset list
```

### /dk axiom datasets create <name>

Create a new dataset:

```bash
axiom dataset create --name="$NAME" --description="$DESCRIPTION"
```

**Naming conventions:**

- Use lowercase with hyphens: `app-logs`, `http-requests`
- Environment suffix: `logs-prod`, `logs-dev`

### /dk axiom datasets delete <name>

Delete a dataset (requires confirmation):

```bash
axiom dataset delete $NAME
```

**CRITICAL:** This permanently deletes all data. Use `--force` only if absolutely sure.

---

## /dk axiom query

Execute APL (Axiom Processing Language) query:

```bash
axiom query "['dataset'] | where level == 'error' | limit 10"
```

### Common APL Queries

```apl
# Recent errors
['logs'] | where level == 'error' | sort by _time desc | limit 50

# Status code distribution
['http-logs'] | summarize count() by status

# Slow requests (>1s)
['http-logs'] | where duration > 1000 | sort by duration desc

# Errors by service
['logs'] | where level == 'error' | summarize count() by service

# Last 24h summary
['logs'] | where _time > ago(24h) | summarize count() by bin(_time, 1h)

# Search by message
['logs'] | where message contains "failed" | limit 100
```

---

## /dk axiom stream

Livestream logs from dataset (real-time tail):

```bash
axiom stream $DATASET
```

Filter stream:

```bash
axiom stream $DATASET --filter="level == 'error'"
```

---

## /dk axiom ingest

Ingest data from stdin or file:

```bash
# From JSON file
cat events.json | axiom ingest $DATASET

# Single event
echo '{"level":"info","message":"test"}' | axiom ingest $DATASET
```

---

## /dk axiom web

Open Axiom dashboard in browser:

```bash
axiom web
```

---

## /dk axiom test

Send test event to verify connectivity:

```bash
uv run python -c "
from lib.axiom import send_test_event
ok, msg = send_test_event('test-logs')
print('OK' if ok else 'FAILED', msg)
"
```

---

## /dk axiom token

Show token information:

```bash
uv run python -c "
from lib.axiom import check_token
has_token, info = check_token()
print('Token:', info['masked_token'] or 'Not set')
print('Source:', info['source'] or 'None')
print('Dataset:', info['dataset'] or 'Not configured')
"
```

### /dk axiom token create

Opens Axiom token settings page:

```bash
open https://app.axiom.co/settings/api-tokens
```

**Token Types:**

| Type     | Use Case                 | Permissions         |
| -------- | ------------------------ | ------------------- |
| Basic    | Ingest only (frontend)   | Ingest to 1 dataset |
| Advanced | Query + Ingest (backend) | Query, Ingest, CRUD |

**Workflow:**

1. Go to Settings > API tokens
2. Create **Advanced Token** with:
   - Dataset: select or "All datasets"
   - Permissions: Query, Ingest
3. Copy token to `.env.local`: `AXIOM_TOKEN=xaat-xxx`
4. `/dk axiom token test` to verify
5. `/dk env sync` to push to Vercel

### /dk axiom token test

Validate token with API call:

```bash
uv run python -c "
from lib.axiom import validate_token
ok, msg = validate_token()
print('OK' if ok else 'FAILED', msg)
"
```

---

## Security Best Practices

**CRITICAL: Frontend Logging**

Frontend-Logs sollten **NUR** ueber einen Proxy laufen:

```
Client -> /api/log (Next.js Route) -> Axiom
```

**NIEMALS** Token auf Client-Seite exponieren:

```typescript
// WRONG - exposes token
const axiom = new Axiom({ token: process.env.NEXT_PUBLIC_AXIOM_TOKEN });

// CORRECT - use server-side proxy
// app/api/log/route.ts
export async function POST(req: Request) {
  const data = await req.json();
  await axiom.ingest("logs", data);
  return Response.json({ ok: true });
}
```

**Environment Variables:**

| Variable                    | Where     | Purpose              |
| --------------------------- | --------- | -------------------- |
| `AXIOM_TOKEN`               | Server    | Backend ingest/query |
| `AXIOM_DATASET`             | Server    | Default dataset      |
| `NEXT_PUBLIC_AXIOM_DATASET` | Client OK | Dataset name only    |
| `NEXT_PUBLIC_AXIOM_TOKEN`   | **NEVER** | Exposes credentials  |

---

## Configuration

Add to `config.jsonc`:

```jsonc
"logging": {
  "services": {
    "axiom": {
      "provider": "axiom",
      "dataset": "logs"
    }
  }
}
```

---

## Next.js Integration

### With @axiomhq/nextjs (Recommended)

```bash
npm install @axiomhq/nextjs
```

```typescript
// lib/axiom.ts (server-side only)
import { Axiom } from "@axiomhq/js";

export const axiom = new Axiom({
  token: process.env.AXIOM_TOKEN!,
});

// Flush on serverless function end
export const flushAxiom = () => axiom.flush();
```

### Web Vitals (via proxy)

```typescript
// app/api/vitals/route.ts
import { axiom } from "@/lib/axiom";

export async function POST(req: Request) {
  const vitals = await req.json();
  await axiom.ingest(process.env.AXIOM_DATASET!, vitals);
  return Response.json({ ok: true });
}
```

---

## Troubleshooting

| Issue             | Solution                                 |
| ----------------- | ---------------------------------------- |
| CLI not found     | `brew install axiom`                     |
| Not authenticated | `axiom auth login`                       |
| Token invalid     | Check token permissions in settings      |
| Dataset not found | Create with `/dk axiom datasets create`  |
| Query timeout     | Add time filter: `where _time > ago(1h)` |
| Ingest failed     | Check dataset write permissions          |
