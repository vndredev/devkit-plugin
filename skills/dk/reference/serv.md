# /dk serv

**CRITICAL:** Unified service management for local development.

**YOU MUST use `/dk serv` commands for ALL dev service operations.**

## Commands

| Command          | Description                       |
| ---------------- | --------------------------------- |
| `/dk serv`       | Status aller Services             |
| `/dk serv start` | Zeigt alle Start-Commands         |
| `/dk serv stop`  | Stoppt alle Services              |
| `/dk serv urls`  | Zeigt alle URLs                   |
| `/dk serv test`  | Sendet Test-Events (Stripe, etc.) |

---

## Configuration

Add to `.claude/.devkit/config.jsonc`:

```jsonc
{
  "dev": {
    "command": "npm run dev", // oder "bun dev", "pnpm dev", etc.
    "port": 3000,
    "include_webhooks": true, // ob /dk serv start auch webhooks startet
  },
  "webhooks": {
    "ngrok": {
      "domain": "your-app.ngrok-free.app",
      "port": 3000,
    },
    "services": {
      "stripe": {
        "path": "/api/webhooks/stripe",
        "provider": "stripe",
      },
    },
  },
}
```

---

## /dk serv

Show status of all services:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.serv import serv_status

status = serv_status()

print('=== Dev Server ===')
print(f'Command: {status[\"dev\"][\"command\"]}')
print(f'Port: {status[\"dev\"][\"port\"]}')
print(f'Include webhooks: {status[\"dev\"][\"include_webhooks\"]}')

print()
print('=== CLI Status ===')
print(f'ngrok: {status[\"ngrok\"][\"message\"]}')
print(f'Stripe CLI: {status[\"stripe_cli\"][\"message\"]}')

print()
print('=== Configuration ===')
if status['ngrok']['domain']:
    print(f'Domain: {status[\"ngrok\"][\"domain\"]}')
else:
    print('No ngrok domain configured')

print()
print('=== Detected Services ===')
for name, info in status['services'].items():
    print(f'{name}: {info[\"path\"]} (from {info[\"detected_from\"]})')

if not status['services']:
    print('No webhook services detected')
"
```

---

## /dk serv start

Show commands to start all services (respects `include_webhooks` setting):

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.serv import serv_start_commands

commands = serv_start_commands()

print('=== Start Commands ===')
print()
print('Run these commands in separate terminals:')
print()

for cmd in commands:
    print(f'Terminal {cmd[\"terminal\"]}: {cmd[\"description\"]}')
    print(f'  {cmd[\"command\"]}')
    print()
"
```

**Manual Start** (copy to separate terminals):

```bash
# Terminal 1: Dev server
npm run dev

# Terminal 2: ngrok tunnel (if configured)
ngrok http 3000 --domain your-app.ngrok-free.app

# Terminal 3: Stripe CLI (if Stripe detected)
stripe listen --forward-to http://localhost:3000/api/webhooks/stripe
```

---

## /dk serv stop

Stop all services:

```bash
# Find and kill processes by port
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:4040 | xargs kill -9 2>/dev/null || true  # ngrok inspect

# Or use process names
pkill -f "ngrok" 2>/dev/null || true
pkill -f "stripe listen" 2>/dev/null || true
```

**Note:** The dev server should be stopped via its terminal (Ctrl+C).

---

## /dk serv urls

Show all service URLs:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.serv import serv_urls

urls = serv_urls()

print('=== Service URLs ===')
print()
print(f'Localhost: {urls[\"localhost\"]}')

if urls['ngrok']:
    print(f'ngrok: {urls[\"ngrok\"]}')
else:
    print('ngrok: Not configured')

if urls['webhooks']:
    print()
    print('=== Webhook URLs ===')
    print('Configure these in provider dashboards:')
    print()
    for wh in urls['webhooks']:
        print(f'{wh[\"service\"]}:')
        print(f'  URL: {wh[\"url\"]}')
        if wh['dashboard']:
            print(f'  Dashboard: {wh[\"dashboard\"]}')
        print()
"
```

---

## /dk serv test

Send test webhook events (Stripe only for now):

```bash
# Stripe test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created
stripe trigger invoice.payment_failed

# List all available Stripe triggers
stripe trigger --help
```

---

## Prerequisites

- **Dev server**: Your project's dev command (npm, bun, pnpm, etc.)
- **ngrok** (optional): `brew install ngrok/ngrok/ngrok && ngrok config add-authtoken <TOKEN>`
- **Stripe CLI** (optional): `brew install stripe/stripe-cli/stripe && stripe login`

---

## Workflow

1. **Configure** `dev` section in config.jsonc
2. **Run `/dk serv`** to check status
3. **Run `/dk serv start`** to get all commands
4. **Start terminals** with shown commands
5. **Run `/dk serv urls`** to get URLs for dashboards
6. **Test** with `/dk serv test` or provider dashboard

---

## include_webhooks Setting

The `dev.include_webhooks` setting controls whether `/dk serv start` includes webhook-related commands:

| Value   | Behavior                                             |
| ------- | ---------------------------------------------------- |
| `true`  | Shows dev server + ngrok + Stripe CLI commands       |
| `false` | Shows only dev server command (for non-webhook apps) |

Example for a simple Python project:

```jsonc
{
  "dev": {
    "command": "uv run python -m http.server",
    "port": 8000,
    "include_webhooks": false,
  },
}
```

---

## Troubleshooting

### Dev server not starting

```bash
# Check if port is in use
lsof -i:3000

# Kill process on port
lsof -ti:3000 | xargs kill -9
```

### ngrok not connecting

```bash
# Check ngrok auth
ngrok config check

# Re-authenticate
ngrok config add-authtoken <YOUR_TOKEN>
```

### Stripe CLI not forwarding

```bash
# Check Stripe login
stripe config --list

# Re-login
stripe login
```
