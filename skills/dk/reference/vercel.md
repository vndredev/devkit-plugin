# Vercel Module

Connect and manage Vercel deployments.

## Commands

| Command              | Description                |
| -------------------- | -------------------------- |
| `/dk vercel connect` | Link project to Vercel     |
| `/dk vercel env`     | Sync environment variables |

## /dk vercel connect

Link the current project to Vercel for automatic deployments:

```bash
# Check if already linked
if [ -d ".vercel" ]; then
    echo "✓ Project already linked to Vercel"
    vercel project ls 2>/dev/null | head -5
    exit 0
fi

# Link project
echo "Linking project to Vercel..."
vercel link

# Show project info
echo ""
echo "Project linked! Next steps:"
echo "1. Push to GitHub to trigger automatic deployments"
echo "2. Or run 'vercel deploy' for manual deployment"
```

After linking:

- `.vercel/` directory created
- Project connected to Vercel dashboard
- Automatic deployments on push (if GitHub connected)

## /dk vercel env

Sync environment variables from `.env.local` to Vercel:

```bash
# Check for .env.local
if [ ! -f ".env.local" ]; then
    echo "No .env.local found"
    exit 1
fi

echo "Syncing environment variables to Vercel..."
echo "Select environment: development, preview, or production"
```

Claude will:

1. Read `.env.local` (excluding secrets like API keys)
2. Ask which environment to sync to
3. Use `vercel env add` for each variable

**Security Note**: Never sync sensitive keys automatically. Claude will skip variables containing:

- `SECRET`
- `KEY`
- `TOKEN`
- `PASSWORD`

## Prerequisites

- Vercel account
- `vercel` CLI installed: `npm i -g vercel`
- Authenticated: `vercel login`

## Vercel Project Structure

After `/dk vercel connect`:

```
.vercel/
├── project.json    # Project ID & Org ID
└── README.txt      # Vercel info
```

## Integration with NeonDB

For automatic database branches per preview deployment, use the **native Neon-Vercel integration**:

1. Go to Vercel Dashboard → Integrations → Neon
2. Connect your Neon project
3. Enable "Create branch per preview"

This integration:

- Creates DB branch per Vercel preview deployment
- Sets `DATABASE_URL` automatically
- Cleans up branches when deployments are deleted
