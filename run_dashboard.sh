#!/bin/bash
# Portugal New Companies - Dashboard Launcher
# Usage: ./run_dashboard.sh [port]

set -e
cd "$(dirname "$0")"

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Get IPs
TAILSCALE_IP=$(tailscale ip -1 2>/dev/null || echo "N/A")
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
PORT="${1:-8501}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║       🇵🇹 Portugal New Companies Dashboard                ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  🌐 Tailscale:  http://${TAILSCALE_IP}:${PORT}"
echo "║  🌐 Public:     http://${PUBLIC_IP}:${PORT}"
echo "║  🌐 Local:      http://localhost:${PORT}"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uv run streamlit run dashboard.py \
    --server.address 0.0.0.0 \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false
