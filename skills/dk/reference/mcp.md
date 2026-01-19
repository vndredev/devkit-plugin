# /dk mcp

**MCP Server Management für devkit-plugin.**

## Enthaltene MCP-Server

Das Plugin stellt folgende MCP-Server bereit:

| Server       | Package                         | Description           | Env Vars                           |
| ------------ | ------------------------------- | --------------------- | ---------------------------------- |
| `context7`   | `@upstash/context7-mcp`         | Library documentation | -                                  |
| `neon`       | `@neondatabase/mcp-server-neon` | Postgres database     | `NEON_API_KEY`                     |
| `stripe`     | `@stripe/mcp`                   | Payment integration   | `STRIPE_SECRET_KEY`                |
| `playwright` | `@playwright/mcp`               | Browser automation    | -                                  |
| `axiom`      | `mcp-server-axiom`              | Observability/Logging | `AXIOM_TOKEN`, `AXIOM_ORG_ID`      |
| `upstash`    | `@upstash/mcp-server`           | Redis database        | `UPSTASH_EMAIL`, `UPSTASH_API_KEY` |

---

## API Keys Configuration

Set required API keys in your shell environment:

```bash
# ~/.zshrc or ~/.bashrc

# Neon (https://console.neon.tech/app/settings/api-keys)
export NEON_API_KEY="neon_api_key_here"

# Stripe (https://dashboard.stripe.com/apikeys)
export STRIPE_SECRET_KEY="sk_test_..."

# Axiom (https://app.axiom.co/settings/api-tokens)
export AXIOM_TOKEN="your-axiom-token"
export AXIOM_ORG_ID="your-org-id"

# Upstash (https://console.upstash.com/account/api)
export UPSTASH_EMAIL="your-email@example.com"
export UPSTASH_API_KEY="your-upstash-api-key"
```

After setting keys: **Restart Claude Code**.

**Note:** MCPs with missing env vars will start but fail to connect. Use `${VAR:-}` syntax in configs for graceful fallback.

---

## /dk mcp check

Check MCP server status and env var configuration:

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.mcp import format_mcp_status
print(format_mcp_status())
"
```

This checks:

- Which env vars are set in current environment
- Which env vars are exported in shell config (~/.zshrc or ~/.bashrc)
- Server readiness status

---

## MCP Status (Claude CLI)

```bash
# List all MCPs
claude mcp list

# Test specific MCP
claude mcp test neon
```

---

## Einzelne MCPs deaktivieren

Falls du einen MCP nicht nutzen möchtest, kannst du ihn in deiner lokalen `.claude/settings.json` deaktivieren:

```json
{
  "mcpServers": {
    "axiom": {
      "disabled": true
    }
  }
}
```

---

## Troubleshooting

### MCP startet nicht

1. Prüfe ob Node.js >= 18 installiert ist
2. Prüfe ob API Keys korrekt gesetzt sind
3. Starte Claude Code mit `claude --debug` für Details

### Context7 zeigt keine Ergebnisse

Context7 benötigt keinen API Key, aber:

- Nutze `resolve-library-id` vor `query-docs`
- Prüfe Library-Namen (z.B. "react" nicht "React.js")

### Neon-Verbindung fehlgeschlagen

```bash
# API Key testen
curl -H "Authorization: Bearer $NEON_API_KEY" \
  https://console.neon.tech/api/v2/projects
```

### Stripe-Tools nicht verfügbar

```bash
# API Key testen
curl -u "$STRIPE_SECRET_KEY:" https://api.stripe.com/v1/balance
```

### Upstash-Verbindung fehlgeschlagen

```bash
# API Key testen
curl -H "Authorization: Bearer $UPSTASH_API_KEY" \
  -H "Email: $UPSTASH_EMAIL" \
  https://api.upstash.com/v2/redis/databases
```

---

## Ressourcen

- [Context7 Docs](https://upstash.com/docs/context7)
- [Neon MCP Docs](https://neon.com/docs/ai/neon-mcp-server)
- [Stripe MCP Docs](https://docs.stripe.com/mcp)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
- [Axiom MCP](https://axiom.co/docs/console/intelligence/mcp-server)
- [Upstash MCP Docs](https://upstash.com/docs/redis/integrations/mcp)
