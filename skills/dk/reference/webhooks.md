# /dk webhooks

**CRITICAL:** Webhook tunnel management for local development.

**YOU MUST use `/dk webhooks` commands for ALL webhook setup.**

## Commands

| Command              | Description                        |
| -------------------- | ---------------------------------- |
| `/dk webhooks`       | Show status and detected services  |
| `/dk webhooks start` | Start ngrok + provider CLIs        |
| `/dk webhooks urls`  | Show webhook URLs for dashboards   |
| `/dk webhooks test`  | Send test events (where supported) |

---

## Prerequisites

- **ngrok**: `brew install ngrok/ngrok/ngrok && ngrok config add-authtoken <TOKEN>`
- **Stripe CLI** (optional): `brew install stripe/stripe-cli/stripe && stripe login`

---

## Configuration

Add to `.claude/.devkit/config.jsonc`:

```jsonc
{
  "webhooks": {
    "ngrok": {
      "domain": "your-app.ngrok-free.app", // Static domain from ngrok dashboard
      "port": 3000, // Local dev server port
    },
    "services": {
      "stripe": {
        "path": "/api/webhooks/stripe",
        "provider": "stripe",
        "events": [
          "checkout.session.completed",
          "customer.subscription.updated",
        ],
      },
      "clerk": {
        "path": "/api/webhooks/clerk",
        "provider": "clerk",
      },
    },
  },
}
```

---

## /dk webhooks

Show webhook status and detected services:

```bash
uv run python -c "
from lib.webhooks import webhooks_status
import json

status = webhooks_status()

print('=== CLI Status ===')
print(f'ngrok: {status[\"ngrok\"][\"message\"]}')
print(f'Stripe CLI: {status[\"stripe_cli\"][\"message\"]}')

print()
print('=== Configuration ===')
if status['ngrok']['domain']:
    print(f'Domain: {status[\"ngrok\"][\"domain\"]}')
    print(f'Port: {status[\"ngrok\"][\"port\"]}')
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

## /dk webhooks start

Start ngrok tunnel and provider CLIs:

```bash
uv run python -c "
from lib.webhooks import webhooks_start

print('=== Starting Webhook Tunnels ===')
for step, ok, msg in webhooks_start():
    status = '✓' if ok else '✗'
    print(f'{status} {step}: {msg}')
"
```

**Manual Start** (run in separate terminals):

```bash
# Terminal 1: ngrok tunnel
ngrok http 3000 --domain your-app.ngrok-free.app

# Terminal 2: Stripe CLI (if using Stripe)
stripe listen --forward-to http://localhost:3000/api/webhooks/stripe
```

---

## /dk webhooks urls

Show webhook URLs to configure in provider dashboards:

```bash
uv run python -c "
from lib.webhooks import webhooks_urls

print('=== Webhook URLs ===')
print('Configure these URLs in provider dashboards:')
print()

for service, url, dashboard in webhooks_urls():
    print(f'{service}:')
    print(f'  URL: {url}')
    if dashboard:
        print(f'  Dashboard: {dashboard}')
    print()
"
```

---

## /dk webhooks test

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

## Auto-Detection

Services are auto-detected from:

| Source       | Detection Method                       |
| ------------ | -------------------------------------- |
| Config       | `webhooks.services` in config.jsonc    |
| Routes       | `/app/api/webhooks/*/route.ts`         |
| Environment  | `STRIPE_*`, `CLERK_*`, `LIVEKIT_*` etc |
| Dependencies | package.json `stripe`, `@clerk/nextjs` |

---

## Provider Matrix

| Provider | CLI        | Auto-Forward | Dashboard URL                         |
| -------- | ---------- | ------------ | ------------------------------------- |
| Stripe   | stripe-cli | Yes          | https://dashboard.stripe.com/webhooks |
| Clerk    | -          | ngrok only   | https://dashboard.clerk.com           |
| LiveKit  | -          | ngrok only   | https://cloud.livekit.io              |
| Resend   | -          | ngrok only   | https://resend.com/webhooks           |

---

## Workflow

1. **Configure ngrok domain** in config.jsonc
2. **Run `/dk webhooks`** to check status
3. **Run `/dk webhooks urls`** to get URLs
4. **Configure webhooks** in provider dashboards
5. **Run `/dk webhooks start`** to start tunnels
6. **Test** with `/dk webhooks test` or provider dashboard

---

## Troubleshooting

### ngrok not starting

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

### Webhooks not reaching app

1. Check ngrok is running: `curl https://your-domain.ngrok-free.app`
2. Check route exists: `ls app/api/webhooks/`
3. Check dev server is running on correct port
4. Check Stripe CLI output for errors

---

## Common Events

### Stripe

```
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.paid
invoice.payment_failed
```

### Clerk

```
user.created
user.updated
user.deleted
session.created
```

### LiveKit

```
room_started
room_finished
participant_joined
participant_left
```
