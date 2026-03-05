#!/usr/bin/env python3
"""
Scheduled job to fetch new companies daily
Can be run via cron or as a daemon
"""

import time
import schedule
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))
from scraper import fetch_new_companies, save_companies


def job():
    """Daily job to fetch new companies"""
    print(f"\n{'='*50}")
    print(f"🕐 Running scheduled fetch: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    try:
        companies = fetch_new_companies()
        if companies:
            save_companies(companies)
        else:
            print("❌ No companies fetched")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("📅 Portugal New Companies Tracker - Scheduler")
    print("   Fetches new companies daily at 09:00 Europe/Madrid")
    print("   Press Ctrl+C to stop\n")
    
    # Run once on start
    job()
    
    # Schedule daily at 9 AM
    schedule.every().day.at("09:00").do(job)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
