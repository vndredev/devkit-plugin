# /dk livekit

**CRITICAL:** LiveKit real-time communication management via `lk` CLI.

## Prerequisites

- LiveKit CLI installed: `brew install livekit-cli` or `go install github.com/livekit/livekit-cli/cmd/lk@latest`
- Project configured: `lk project add`

## Commands

| Command                               | Description               |
| ------------------------------------- | ------------------------- |
| `/dk livekit`                         | Show status + auth        |
| `/dk livekit project`                 | Show project config       |
| `/dk livekit project add`             | Add project (interactive) |
| `/dk livekit project list`            | List configured projects  |
| `/dk livekit project remove <name>`   | Remove project config     |
| `/dk livekit room list`               | List active rooms         |
| `/dk livekit room create <name>`      | Create room               |
| `/dk livekit room delete <name>`      | Delete room               |
| `/dk livekit token <room> <id>`       | Generate access token     |
| `/dk livekit participant list <room>` | List participants         |
| `/dk livekit egress list`             | List recordings           |
| `/dk livekit join <room>`             | Debug join (CLI)          |
| `/dk livekit web`                     | Open cloud dashboard      |

---

## /dk livekit

Show LiveKit status (CLI, project, rooms):

```bash
echo "=== LiveKit Status ==="
echo ""

# Check CLI
if command -v lk &>/dev/null; then
  VERSION=$(lk --version 2>/dev/null || echo "unknown")
  echo "CLI: OK ($VERSION)"
else
  echo "CLI: Not installed"
  echo "  Install: brew install livekit-cli"
  echo "       or: go install github.com/livekit/livekit-cli/cmd/lk@latest"
fi

echo ""

# Check project config
if lk project list 2>/dev/null | grep -q .; then
  echo "Projects:"
  lk project list
else
  echo "Projects: None configured"
  echo "  Setup: lk project add"
fi

echo ""

# Active rooms
ROOMS=$(lk room list 2>/dev/null | grep -c "^" || echo "0")
echo "Active Rooms: $ROOMS"

echo ""
echo "Dashboard: https://cloud.livekit.io"
```

---

## /dk livekit project

Show current project configuration:

```bash
lk project list
```

### /dk livekit project add

Add a new project (interactive):

```bash
lk project add
```

**This prompts for:**

- Project name (for local reference)
- API URL (e.g., `wss://myproject.livekit.cloud`)
- API Key
- API Secret

**From LiveKit Cloud:**

1. Go to https://cloud.livekit.io
2. Select project → Settings → Keys
3. Copy API Key and Secret

### /dk livekit project list

List all configured projects:

```bash
lk project list
```

### /dk livekit project remove <name>

Remove a project configuration:

```bash
lk project remove $NAME
```

---

## /dk livekit room list

List all active rooms:

```bash
lk room list
```

Output columns: Name, SID, Participants, Created

### /dk livekit room create <name>

Create a new room:

```bash
ROOM_NAME="${1}"
if [ -z "$ROOM_NAME" ]; then
  echo "Usage: /dk livekit room create <name>"
  exit 1
fi

lk room create --name="$ROOM_NAME"
```

**Optional flags:**

- `--empty-timeout=300` - Auto-delete after N seconds empty (default: 300)
- `--max-participants=10` - Limit participants

### /dk livekit room delete <name>

Delete a room:

```bash
ROOM_NAME="${1}"
if [ -z "$ROOM_NAME" ]; then
  echo "Usage: /dk livekit room delete <name>"
  exit 1
fi

lk room delete "$ROOM_NAME"
```

---

## /dk livekit token

Generate access token for room:

```bash
ROOM="${1}"
IDENTITY="${2}"

if [ -z "$ROOM" ] || [ -z "$IDENTITY" ]; then
  echo "Usage: /dk livekit token <room> <identity>"
  exit 1
fi

lk token create \
  --room="$ROOM" \
  --identity="$IDENTITY" \
  --join \
  --valid-for=24h
```

**Token permissions (flags):**

- `--join` - Can join room
- `--publish` - Can publish tracks
- `--subscribe` - Can subscribe to tracks
- `--publish-data` - Can send data messages
- `--admin` - Room admin (can mute/kick)

**Example with full permissions:**

```bash
lk token create \
  --room="my-room" \
  --identity="user-123" \
  --join --publish --subscribe --publish-data \
  --valid-for=24h
```

---

## /dk livekit participant list

List participants in a room:

```bash
ROOM="${1}"
if [ -z "$ROOM" ]; then
  echo "Usage: /dk livekit participant list <room>"
  exit 1
fi

lk room participant list "$ROOM"
```

---

## /dk livekit egress list

List all egress (recordings/streams):

```bash
lk egress list
```

**Egress types:**

- Room composite - Record entire room
- Track composite - Record specific tracks
- Track egress - Record single track

---

## /dk livekit join

Debug join a room via CLI (opens browser):

```bash
ROOM="${1:-test-room}"

lk room join "$ROOM" --identity="cli-debug"
```

**Useful for:**

- Testing room connectivity
- Debugging participant issues
- Quick audio/video testing

---

## /dk livekit web

Open LiveKit Cloud dashboard:

```bash
open https://cloud.livekit.io
```

---

## Environment Variables

For application integration, add to `.env.local`:

```bash
LIVEKIT_API_KEY="APIxxxxxxxx"
LIVEKIT_API_SECRET="xxxxxxxxxxxxxxxxxxxxxxxx"
LIVEKIT_URL="wss://myproject.livekit.cloud"
```

---

## Next.js Integration

### Server-side Token Generation

```typescript
// app/api/livekit/token/route.ts
import { AccessToken } from "livekit-server-sdk";

export async function POST(req: Request) {
  const { room, username } = await req.json();

  const at = new AccessToken(
    process.env.LIVEKIT_API_KEY!,
    process.env.LIVEKIT_API_SECRET!,
    {
      identity: username,
      ttl: "24h",
    },
  );

  at.addGrant({ room, roomJoin: true, canPublish: true, canSubscribe: true });

  return Response.json({ token: await at.toJwt() });
}
```

### Client-side Components

```bash
npm install @livekit/components-react livekit-client
```

```tsx
// components/VideoRoom.tsx
"use client";

import { LiveKitRoom, VideoConference } from "@livekit/components-react";
import "@livekit/components-styles";

export function VideoRoom({ token, room }: { token: string; room: string }) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
      connect={true}
    >
      <VideoConference />
    </LiveKitRoom>
  );
}
```

---

## Troubleshooting

| Issue                  | Solution                                   |
| ---------------------- | ------------------------------------------ |
| CLI not found          | `brew install livekit-cli`                 |
| No projects configured | `lk project add`                           |
| Connection refused     | Check LIVEKIT_URL (wss:// not https://)    |
| Token invalid          | Verify API Key/Secret match project        |
| Room not found         | Room may have auto-deleted (empty-timeout) |
| Permission denied      | Check token grants match required action   |

---

## Common Workflows

### Quick Test Room

```bash
# 1. Create room
lk room create --name="test-room"

# 2. Generate token
lk token create --room="test-room" --identity="tester" --join --publish

# 3. Join (opens browser)
lk room join "test-room" --identity="tester"
```

### Production Setup

1. Create project in LiveKit Cloud
2. Add to CLI: `lk project add`
3. Set env vars in `.env.local`
4. Implement token endpoint
5. Test with `/dk livekit room create test`
