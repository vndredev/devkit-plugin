#!/bin/bash
# Service starter for devkit-plugin
# Starts dev server, ngrok, and provider CLIs as background processes
#
# Usage: serv-start.sh <project_dir> <plugin_root>
#
# Creates in project_dir:
#   .serv/dev.log     - Dev server output
#   .serv/ngrok.log   - ngrok output
#   .serv/stripe.log  - Stripe CLI output
#   .serv/pids        - Process IDs for stopping

set -e

PROJECT_DIR="${1:-.}"
PLUGIN_ROOT="${2:-}"

if [ -z "$PLUGIN_ROOT" ]; then
    echo "❌ Usage: serv-start.sh <project_dir> <plugin_root>"
    exit 1
fi

cd "$PROJECT_DIR"

# Create .serv directory for logs and pids
mkdir -p .serv

# Get configuration from Python
CONFIG=$(PYTHONPATH="${PLUGIN_ROOT}/src" python3 -c "
import json
from lib.config import get
from lib.serv import serv_start_commands

commands = serv_start_commands()
config = {
    'commands': commands,
    'port': get('dev.port', 3000),
}
print(json.dumps(config))
" 2>/dev/null)

if [ -z "$CONFIG" ]; then
    echo "❌ Failed to read configuration"
    exit 1
fi

# Clear old pids
> .serv/pids

echo "🚀 Starting services..."
echo ""

# Start each service using Python for proper process handling
echo "$CONFIG" | python3 -c "
import sys
import json
import subprocess
import os

config = json.load(sys.stdin)
commands = config['commands']
port = config['port']
pids = []

for cmd in commands:
    desc = cmd['description']
    command = cmd['command']
    terminal = cmd['terminal']

    # Determine log file based on description
    if 'dev' in desc.lower() or 'server' in desc.lower():
        log_file = '.serv/dev.log'
        name = 'dev'
    elif 'ngrok' in desc.lower():
        log_file = '.serv/ngrok.log'
        name = 'ngrok'
    elif 'stripe' in desc.lower():
        log_file = '.serv/stripe.log'
        name = 'stripe'
    else:
        log_file = f'.serv/service-{terminal}.log'
        name = f'service-{terminal}'

    # Start process
    with open(log_file, 'w') as log:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        pids.append((name, proc.pid))
        print(f'✓ {desc}')
        print(f'  PID: {proc.pid}')
        print(f'  Log: {log_file}')
        print()

# Write pids
with open('.serv/pids', 'w') as f:
    for name, pid in pids:
        f.write(f'{name}:{pid}\n')

print('---')
print(f'Started {len(pids)} service(s)')
print(f'Local: http://localhost:{port}')
print()
print('Logs: .serv/*.log')
print('Stop: /dk serv stop')
"
