#!/usr/bin/env bash
# Setup script for family-meeting MCP server on macOS.
# Creates a venv, installs dependencies, and configures Claude Desktop.
set -e -u -o pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

echo "=== Family Meeting MCP Server Setup ==="
echo "Project directory: $PROJECT_DIR"
echo

# --- 1. Check for uv ---
if ! command -v uv &>/dev/null; then
    echo "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the path so uv is available in this session
    export PATH="$HOME/.local/bin:$PATH"
    echo "uv installed."
else
    echo "uv found: $(uv --version)"
fi

# --- 2. Create venv and install dependencies ---
echo
echo "Creating virtual environment and installing dependencies..."
uv venv "$VENV_DIR" --python 3.12
uv pip install --python "$VENV_DIR/bin/python" -r "$PROJECT_DIR/requirements.txt"
echo "Dependencies installed."

# --- 3. Check for .env ---
echo
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "WARNING: No .env file found!"
    echo "Copy the example and fill in your values:"
    echo "  cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env"
    echo "  # Then edit .env with your API keys"
    echo
    echo "Required variables: ANTHROPIC_API_KEY, NOTION_TOKEN, NOTION_*_DB,"
    echo "  GOOGLE_CALENDAR_*_ID, YNAB_ACCESS_TOKEN, YNAB_BUDGET_ID"
    echo
    read -rp "Continue without .env? (y/N) " yn
    case $yn in
        [Yy]*) echo "Continuing — you'll need to create .env before using the server." ;;
        *) echo "Setup paused. Create .env and re-run this script."; exit 1 ;;
    esac
else
    echo ".env file found."
fi

# --- 4. Check for Google Calendar credentials ---
echo
if [ ! -f "$PROJECT_DIR/token.json" ]; then
    echo "NOTE: No token.json found for Google Calendar."
    echo "Run this to authenticate: $VENV_DIR/bin/python $PROJECT_DIR/scripts/setup_calendar.py"
fi

# --- 5. Configure Claude Desktop ---
echo
PYTHON_PATH="$VENV_DIR/bin/python"
SERVER_PATH="$PROJECT_DIR/src/mcp_server.py"

# Build the server config JSON
SERVER_CONFIG=$(cat <<JSONEOF
{
  "command": "$PYTHON_PATH",
  "args": ["$SERVER_PATH"]
}
JSONEOF
)

CONFIG_DIR="$(dirname "$CLAUDE_CONFIG")"
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Claude Desktop config directory not found: $CONFIG_DIR"
    echo "Is Claude Desktop installed?"
    echo
    echo "Manual setup — add this to your Claude Desktop MCP config:"
    echo "$SERVER_CONFIG"
    exit 0
fi

# Create or update the config file
if [ -f "$CLAUDE_CONFIG" ]; then
    # Check if family-meeting server is already configured
    if python3 -c "import json; c=json.load(open('$CLAUDE_CONFIG')); exit(0 if 'family-meeting' in c.get('mcpServers',{}) else 1)" 2>/dev/null; then
        echo "family-meeting server already in Claude Desktop config. Updating..."
    else
        echo "Adding family-meeting server to Claude Desktop config..."
    fi

    # Use python to safely merge into existing config
    python3 -c "
import json, sys
config_path = '$CLAUDE_CONFIG'
with open(config_path) as f:
    config = json.load(f)
config.setdefault('mcpServers', {})
config['mcpServers']['family-meeting'] = {
    'command': '$PYTHON_PATH',
    'args': ['$SERVER_PATH']
}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print('Config updated:', config_path)
"
else
    echo "Creating Claude Desktop config..."
    mkdir -p "$CONFIG_DIR"
    python3 -c "
import json
config = {
    'mcpServers': {
        'family-meeting': {
            'command': '$PYTHON_PATH',
            'args': ['$SERVER_PATH']
        }
    }
}
with open('$CLAUDE_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
print('Config created:', '$CLAUDE_CONFIG')
"
fi

# --- 6. Done ---
echo
echo "=== Setup complete! ==="
echo
echo "Next steps:"
echo "  1. Restart Claude Desktop (Cmd+Q, then reopen)"
echo "  2. Look for 'family-meeting' in the MCP tools connector menu"
echo "  3. Try: \"What's on my calendar this week?\""
echo
echo "To test the server manually:"
echo "  $PYTHON_PATH $SERVER_PATH"
