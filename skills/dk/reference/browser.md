# /dk browser

**CRITICAL:** Browser automation for UI verification after frontend changes.

**Uses Claude-in-Chrome MCP tools for browser interaction.**

## Commands

| Command                     | Description                      |
| --------------------------- | -------------------------------- |
| `/dk browser`               | Show browser status and help     |
| `/dk browser verify [path]` | Navigate + Snapshot + Screenshot |
| `/dk browser screenshot`    | Take screenshot of current page  |
| `/dk browser open <url>`    | Open URL in browser              |

---

## Prerequisites

- **Claude-in-Chrome Extension**: Must be installed and connected
- **Dev Server Running**: `npm run dev` or similar on configured port

---

## Configuration

Add to `.claude/.devkit/config.jsonc`:

```jsonc
{
  "hooks": {
    "browser": {
      "enabled": true,
      "dev_server": {
        "url": "http://localhost:3000",
        "wait_seconds": 2,
      },
      "frontend_patterns": ["*.tsx", "*.jsx", "*.vue", "*.css"],
      "prompts": {
        "frontend_changed": "🌐 Frontend changed - verify UI: `/dk browser verify` or browser_snapshot on {url}",
      },
    },
  },
}
```

---

## /dk browser

Show browser status and available commands:

```
Browser Verification Commands:
  /dk browser verify [path]  - Full verification flow
  /dk browser screenshot     - Screenshot only
  /dk browser open <url>     - Open URL

Dev Server: http://localhost:3000
Wait Time: 2s (for hot-reload)
```

---

## /dk browser verify [path]

**Full verification flow for UI changes.**

### Steps

1. **Get browser context** - `tabs_context_mcp`
2. **Create new tab** - `tabs_create_mcp`
3. **Navigate to dev server** - `browser_navigate` to configured URL + path
4. **Wait for hot-reload** - `browser_wait_for` configured seconds
5. **Take accessibility snapshot** - `browser_snapshot`
6. **Take screenshot** - `computer` action=screenshot
7. **Ask user** - "Sieht das UI korrekt aus?"

### MCP Tool Sequence

```python
# 1. Get browser context
tabs_context_mcp(createIfEmpty=True)

# 2. Create new tab
tabs_create_mcp()

# 3. Navigate to dev server (use tabId from step 2)
browser_navigate(url="http://localhost:3000" + path, tabId=<tab_id>)

# 4. Wait for hot-reload
browser_wait_for(time=2, tabId=<tab_id>)

# 5. Accessibility snapshot
browser_snapshot(tabId=<tab_id>)

# 6. Screenshot
computer(action="screenshot", tabId=<tab_id>)

# 7. Ask user for confirmation
```

### Example

```
User: Fix the button styling

Claude: [Edits Button.tsx]

Hook Output:
✓ Formatted: Button.tsx
🌐 Frontend changed - verify UI: `/dk browser verify`

User: /dk browser verify /components

Claude: [Executes verification flow]
        [Shows screenshot]

        "Das Button-Styling wurde aktualisiert. Sieht das korrekt aus?"
```

---

## /dk browser screenshot

**Quick screenshot of current browser state.**

### MCP Tools

```python
# Get current tab context
tabs_context_mcp()

# Take screenshot (use existing tab)
computer(action="screenshot", tabId=<tab_id>)
```

---

## /dk browser open <url>

**Open a specific URL in the browser.**

### MCP Tools

```python
# Get or create browser context
tabs_context_mcp(createIfEmpty=True)

# Create new tab
tabs_create_mcp()

# Navigate to URL
browser_navigate(url=<url>, tabId=<tab_id>)
```

---

## Hook Integration

The PostToolUse hook in `format.py` automatically shows a reminder when frontend files are edited:

| Extension | Reminder Shown |
| --------- | -------------- |
| `.tsx`    | Yes            |
| `.jsx`    | Yes            |
| `.vue`    | Yes            |
| `.svelte` | Yes            |
| `.css`    | Yes            |
| `.scss`   | Yes            |
| `.html`   | Yes            |
| `.astro`  | Yes            |

---

## Troubleshooting

### No browser context

```
Error: No tab context available
```

**Solution**: Make sure Claude-in-Chrome extension is installed and connected.

### Dev server not running

```
Error: Connection refused on localhost:3000
```

**Solution**: Start dev server with `npm run dev`.

### Page not updating

1. Check hot-reload is working
2. Increase `wait_seconds` in config
3. Hard refresh the page manually

### Screenshot not showing changes

1. Wait longer after navigation
2. Check if page finished loading
3. Try `browser_snapshot` first to verify DOM state

---

## Best Practices

1. **Always verify after visual changes** - Colors, spacing, layout
2. **Use snapshot + screenshot** - Snapshot for structure, screenshot for visual
3. **Check responsive** - Resize browser if needed
4. **Test user flows** - Click through to verify interactions
