"""
NIF API Key Rotation Manager
Automatically rotates between multiple API keys to maximize throughput
"""

import os
import time
from typing import List, Dict, Optional
from datetime import datetime

class APIKeyRotator:
    """Manages multiple NIF API keys with automatic rotation"""
    
    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("At least one API key is required")
        
        self.keys = keys
        self.current_index = 0
        self.key_status = {}
        self.rotation_count = 0
        
        # Initialize status for each key
        for i, key in enumerate(keys):
            self.key_status[key] = {
                'index': i,
                'available': True,
                'last_check': None,
                'credits': None
            }
    
    def get_current_key(self) -> str:
        """Get the current active key"""
        return self.keys[self.current_index]
    
    def rotate_key(self) -> str:
        """Rotate to the next available key"""
        old_index = self.current_index
        start_index = self.current_index
        attempts = 0
        
        while attempts < len(self.keys):
            self.current_index = (self.current_index + 1) % len(self.keys)
            key = self.keys[self.current_index]
            
            if self.key_status[key]['available']:
                self.rotation_count += 1
                print(f"[rotate] Key #{old_index + 1} -> Key #{self.current_index + 1}")
                return key
            
            attempts += 1
            
            # If we've tried all keys, wait and reset
            if attempts >= len(self.keys):
                print("[rotate] All keys rate limited. Waiting 65 seconds for reset...")
                time.sleep(65)
                # Reset all keys to available
                for k in self.keys:
                    self.key_status[k]['available'] = True
                self.current_index = 0
                return self.keys[0]
        
        return self.keys[0]
    
    def mark_key_limited(self, key: str, retry_after: int = 60):
        """Mark a key as rate limited"""
        if key not in self.key_status:
            return
        
        self.key_status[key]['available'] = False
        self.key_status[key]['last_check'] = datetime.now()
        
        idx = self.key_status[key]['index'] + 1
        print(f"[rotate] Key #{idx} rate limited. Marking as unavailable.")
        
        # Rotate to next key if this was the current key
        if key == self.get_current_key():
            self.rotate_key()
    
    def update_credits(self, key: str, credits: Dict):
        """Update credit information for a key"""
        if key not in self.key_status:
            return
            
        self.key_status[key]['credits'] = credits
        
        # If no credits left, mark as unavailable
        if credits:
            month = credits.get('month', 0)
            day = credits.get('day', 0)
            if month == 0 or day == 0:
                self.key_status[key]['available'] = False
                idx = self.key_status[key]['index'] + 1
                print(f"[rotate] Key #{idx} has insufficient credits (M:{month}, D:{day})")
    
    def get_status_report(self) -> str:
        """Get a status report of all keys"""
        lines = ["[keys] API Key Status:"]
        for i, key in enumerate(self.keys):
            status = self.key_status[key]
            marker = "->" if i == self.current_index else "  "
            avail = "OK" if status['available'] else "LIMITED"
            creds = status.get('credits', {})
            if creds:
                credit_str = f"M:{creds.get('month', '?')} D:{creds.get('day', '?')} H:{creds.get('hour', '?')}"
            else:
                credit_str = "Credits: Unknown"
            lines.append(f"{marker} Key {i+1}: {avail} {credit_str}")
        return "\n".join(lines)


def load_api_keys() -> List[str]:
    """Load API keys from environment"""
    keys = []
    
    # Load primary key
    key1 = os.getenv("NIF_API_KEY", "")
    if key1:
        keys.append(key1)
    
    # Load additional keys
    for i in range(2, 10):
        key = os.getenv(f"NIF_API_KEY_{i}", "")
        if key:
            keys.append(key)
    
    if not keys:
        raise ValueError("No NIF API keys found in environment")
    
    print(f"[keys] Loaded {len(keys)} API key(s)")
    return keys
