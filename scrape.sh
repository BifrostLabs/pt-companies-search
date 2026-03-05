#!/bin/bash
# Portugal New Companies - Scraper
# Usage: ./scrape.sh

set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"

echo "🔍 Fetching new Portuguese companies..."
uv run python scraper.py
