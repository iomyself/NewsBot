import json
import os
import time

DB_FILE = "data/news_db.json"
MAX_DB_SIZE = 1000 # Keep last 1000 items to avoid file bloating

def load_data():
    """Loads the existing news database."""
    if not os.path.exists(DB_FILE):
        return []
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_data(new_items):
    """
    Saves new items to the database.
    - unique_key: 'link'
    - Deduplicates against existing data.
    - Sorts by 'date' (descending).
    - Trims to MAX_DB_SIZE.
    """
    if not new_items:
        return

    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    current_data = load_data()
    
    # Create a set of existing links for fast lookup
    existing_links = {item['link'] for item in current_data}
    
    added_count = 0
    for item in new_items:
        if item['link'] not in existing_links:
            current_data.append(item)
            existing_links.add(item['link'])
            added_count += 1
            
    if added_count == 0:
        print("No new items to add to database.")
        return

    # Sort: Newest first
    # We assume 'date' is YYYY-MM-DD. 
    # For better sorting, we could use a timestamp, but string sort works for ISO format.
    # To be safe, let's just sort by date string descending.
    current_data.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Trim
    if len(current_data) > MAX_DB_SIZE:
        current_data = current_data[:MAX_DB_SIZE]
        
    # Write back
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        print(f"Database updated. Added {added_count} items. Total: {len(current_data)}")
    except Exception as e:
        print(f"Error saving database: {e}")
