import feedparser
import requests
import re

from datetime import datetime, timezone, timedelta

def clean_html(raw_html):
    # Retrieve text from HTML
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

def fetch_rss_items(url, source_name, config, failed_log=None):
    # Returns a list of dicts: [{'title':..., 'link':...}, ...]
    # config: dict containing 'filter_keywords' and 'max_lookback_hours'
    # failed_log: list to append error dicts to
    print(f"Fetching news from {source_name}...")
    items = [] # Renamed to 'items' to match the function's return, 'news_items' in snippet
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Fetching news from {source_name}...") # Changed 'name' to 'source_name'
        response.raise_for_status() # Keep this for error handling
        rss_text = response.text # Define rss_text from response

        # Parse RSS
        feed = feedparser.parse(rss_text)

        if feed.bozo:
             print(f"Warning: Trouble parsing {source_name} feed (bozo exception). Continuing anyway...")

        if not feed.entries:
            print(f"No entries found for {source_name}.")
            # Debug: print first 200 chars to see what we got
            # print(f"Response snippet: {response.text[:200]}")
            return items

        count = 0
        skipped = 0
        for entry in feed.entries:
            if count >= 10:  # Limit to 10 items per source
                break

            title = entry.get('title', 'No Title') # Use .get for safety
            link = entry.get('link', 'No Link')   # Use .get for safety

            title = entry.get('title', 'No Title') # Use .get for safety
            link = entry.get('link', 'No Link')   # Use .get for safety

            # Keyword Filter
            keywords = config.get('filter_keywords', [])
            if not any(kw in title for kw in keywords):
                skipped += 1
                continue

            # Date Filtering (Time Range)
            # Use feedparser's parsed time (struct_time) if available
            published_time = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_time = entry.published_parsed
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_time = entry.updated_parsed
            
            # Default date string for Feishu
            date_str = time.strftime('%Y-%m-%d')
            
            if published_time:
                # Convert struct_time to datetime (UTC)
                try:
                    dt_object = datetime(*published_time[:6], tzinfo=timezone.utc)
                    
                    # Update date_str from the actual parsed date
                    date_str = dt_object.strftime('%Y-%m-%d')

                    # Check Time Range
                    max_hours = config.get('max_lookback_hours', 24)
                    # Simple comparison: Current UTC time - published time
                    now = datetime.now(timezone.utc)
                    if (now - dt_object) > timedelta(hours=max_hours):
                        # Item is too old
                        continue
                except Exception as e:
                    print(f"   [Date Warning] Failed to parse/compare date for '{title}': {e}. Keeping it.")
            else:
                # Fallback for naive string parsing if struct_time is missing (rare for standard RSS)
                # We keep the old logic just as a backup for 'date_str', but can't strictly filter by hours comfortably.
                published = ""
                if hasattr(entry, 'published'):
                    published = entry.published
                elif hasattr(entry, 'updated'):
                    published = entry.updated
                
                if len(published) >= 10 and published[0:4].isdigit():
                    date_str = published[0:10]


            # Description/Summary
            description = ""
            if hasattr(entry, 'summary'):
                description = entry.summary
            elif hasattr(entry, 'description'):
                description = entry.description
            
            clean_desc = clean_html(description)
            # Limit description length (Feishu text field limit is usually large, but let's be safe, e.g. 1000 chars)
            if len(clean_desc) > 1000:
                clean_desc = clean_desc[:997] + "..."

            print(f"{count+1}. {title}\n   Link: {link}")

            items.append({ # Changed 'news_items' to 'items'
                "title": title,
                "link": link,
                "source": source_name, # Use source_name
                "date": date_str,
                "description": clean_desc
            })
            count += 1

        if skipped > 0:
            print(f"   (Skipped {skipped} items not matching keywords)")

    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        if failed_log is not None:
             failed_log.append({
                 "RssTitle": source_name,
                 "RssUrl": url,
                 "ErrorMessage": str(e)
             })

    print("-" * 40)
    return items # Changed 'news_items' to 'items'

import json
import os
import time

def load_config():
    try:
        with open('rss_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: rss_config.json not found.")
        return []
    except json.JSONDecodeError:
        print("Error: Failed to decode rss_config.json.")
        return []

def load_app_config():
    default_config = {
        "filter_keywords": ["存款", "理财", "经济"],
        "max_lookback_hours": 24
    }
    try:
        if os.path.exists('app_config.json'):
            with open('app_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading app_config.json: {e}. Using defaults.")
    
    return default_config


def get_feishu_config():
    # Try Env Vars first (for GitHub Actions)
    config = {
        "app_id": os.environ.get("FEISHU_APP_ID"),
        "app_secret": os.environ.get("FEISHU_APP_SECRET"),
        "app_token": os.environ.get("FEISHU_APP_TOKEN"),
        "table_id": os.environ.get("FEISHU_TABLE_ID"),
        "error_table_id": os.environ.get("FEISHU_ERROR_TABLE_ID"),
        "error_app_token": os.environ.get("FEISHU_ERROR_APP_TOKEN")
    }
    
    # If any is missing, try loading local config
    if not all(config.values()):
        try:
            with open('feishu_config.json', 'r', encoding='utf-8') as f:
                local_config = json.load(f)
                # Fill missing keys from local config
                for key in config:
                    if not config[key]:
                        config[key] = local_config.get(key)
        except Exception:
            pass # Ignore if file not found or error
            
    return config

TOKEN_FILE = "token.json"

def get_tenant_access_token(app_id, app_secret):
    # 1. Check Cache
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                if data.get('expire_time', 0) > time.time():
                    # print("Using cached token")
                    return data.get('tenant_access_token')
        except:
            pass

    # 2. Fetch New Token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {"app_id": app_id, "app_secret": app_secret}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        res_json = response.json()
        if res_json.get("code") == 0:
            token = res_json.get("tenant_access_token")
            expire = res_json.get("expire", 7200)
            
            # Save to cache (expire_time = now + expire - buffer)
            with open(TOKEN_FILE, 'w') as f:
                json.dump({
                    "tenant_access_token": token,
                    "expire_time": time.time() + expire - 60 
                }, f)
            
            return token
        else:
            print(f"Feishu Auth Error: {res_json}")
            return None
    except Exception as e:
        print(f"Feishu Auth Exception: {e}")
        return None

def push_to_feishu(token, app_token, table_id, records):
    if not records:
        print("No records to push.")
        return
        
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    records_payload = []
    for r in records:
        records_payload.append({
            "fields": {
                "Title": r['title'],
                "Link": r['link'], 
                "Source": r['source'],
                "Date": int(time.mktime(time.strptime(r['date'], "%Y-%m-%d"))) * 1000, # Feishu Date expects timestamp in ms
                "Description": r['description']
            }
        })
        
    data = {"records": records_payload}
    
    try:
        # Batch max 500, we assume records usually < 100
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
             print(f"Feishu API Error ({response.status_code}): {response.text}")
        
        response.raise_for_status()
        res_json = response.json()
        if res_json.get("code") == 0:
            print(f"Successfully pushed {len(records)} records to Feishu.")
        else:
            print(f"Feishu Push Error: {res_json}")
    except Exception as e:
        print(f"Feishu Push Exception: {e}")

def push_errors_to_feishu(token, app_token, table_id, records):
    if not records:
        return

    print(f"Pushing {len(records)} error logs to Feishu...")
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    records_payload = []
    for r in records:
        records_payload.append({
            "fields": {
                "RssTitle": r['RssTitle'],
                "RssUrl": r['RssUrl'],
                "ErrorMessage": r.get('ErrorMessage', 'Unknown Error')
            }
        })

    data = {"records": records_payload}

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
             print(f"Feishu Error Log Push Fail ({response.status_code}): {response.text}")
        
        # We don't raise status for error logging to avoid crashing the main flow
        res_json = response.json()
        if res_json.get("code") == 0:
            print(f"Successfully pushed error logs.")
        else:
            print(f"Feishu Error Log Push Error: {res_json}")
    except Exception as e:
        print(f"Feishu Error Log Push Exception: {e}")

def main():
    print("Starting NewsBot Fetcher...\n" + "="*40)
    
    sources = load_config()
    collected_records = []
    failed_feeds = []
    current_date = time.strftime("%Y-%m-%d") # Keep this for potential fallback or metadata

    # Load RSS sources
    rss_sources = load_config()
    
    if not rss_sources:
        print("No RSS sources loaded. Exiting.")
        return

    # Load App Config
    app_config = load_app_config()
    print(f"Loaded config: Keywords={app_config.get('filter_keywords')}, Max Hours={app_config.get('max_lookback_hours')}")

    # rss_sources is a dict: {"Name": "URL", ...}
    for name, url in rss_sources.items():
        if url:
            items = fetch_rss_items(url, name, app_config, failed_feeds)
            if items:
                collected_records.extend(items)
        else:
            print(f"Skipping source {name}: No URL provided.")
            
    # Feishu Integration
    feishu_conf = get_feishu_config()
    if all(feishu_conf.values()):
        print("Pushing to Feishu...")
        token = get_tenant_access_token(feishu_conf['app_id'], feishu_conf['app_secret'])
        if token:
            push_to_feishu(token, feishu_conf['app_token'], feishu_conf['table_id'], collected_records)
            
            # Push errors if any and if error_table_id is configured
            if failed_feeds and feishu_conf.get('error_table_id'):
                # Use error_app_token if provided, otherwise fallback to main app_token (backward compatibility)
                err_token = feishu_conf.get('error_app_token') or feishu_conf['app_token']
                push_errors_to_feishu(token, err_token, feishu_conf['error_table_id'], failed_feeds)
    else:
        print("Feishu config missing. Skipping upload.")

    print("Done.")

if __name__ == "__main__":
    main()
