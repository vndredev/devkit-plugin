# /dk webhooks

**Webhook configuration status.** Shows what's configured and detected.

**💡 Nutze `/dk serv start` zum Starten aller Services (Dev-Server + Webhooks).**

## Commands

| Command        | Description                  |
| -------------- | ---------------------------- |
| `/dk webhooks` | Webhook configuration status |

**Service-Commands sind jetzt in `/dk serv`:**

| Command          | Description               |
| ---------------- | ------------------------- |
| `/dk serv`       | Status aller Services     |
| `/dk serv start` | Zeigt alle Start-Commands |
| `/dk serv urls`  | Zeigt alle URLs           |
| `/dk serv test`  | Sendet Test-Events        |

---

## /dk webhooks

Show webhook configuration and detected services:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.webhooks import webhooks_status

status = webhooks_status()

print('=== Webhook Configuration ===')
print()

print('CLI Status:')
print(f'  ngrok: {status[\"ngrok\"][\"message\"]}')
print(f'  Stripe CLI: {status[\"stripe_cli\"][\"message\"]}')

print()
print('ngrok Config:')
if status['ngrok']['domain']:
    print(f'  Domain: {status[\"ngrok\"][\"domain\"]}')
    print(f'  Port: {status[\"ngrok\"][\"port\"]}')
else:
    print('  No ngrok domain configured')
    print('  Add webhooks.ngrok.domain to config.jsonc')

print()
print('Detected Services:')
if status['services']:
    for name, info in status['services'].items():
        print(f'  {name}: {info[\"path\"]} (from {info[\"detected_from\"]})')
else:
    print('  No webhook services detected')

print()
print('💡 Nutze \`/dk serv start\` zum Starten aller Services')
"
```

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

## Prerequisites

- **ngrok**: `brew install ngrok/ngrok/ngrok && ngrok config add-authtoken <TOKEN>`
- **Stripe CLI** (optional): `brew install stripe/stripe-cli/stripe && stripe login`

---

## Common Events

### Stripe

```text
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.paid
invoice.payment_failed
```

### Clerk

```text
user.created
user.updated
user.deleted
session.created
```

### LiveKit

```text
room_started
room_finished
participant_joined
participant_left
```
