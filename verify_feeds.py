import xml.etree.ElementTree as ET
import requests
import feedparser
import concurrent.futures
import json
import time

OPML_FILE = "feeds-zh.opml"
OUTPUT_FILE = "rss_config.json"
MAX_WORKERS = 20  # Parallel checks

def parse_opml(file_path):
    feeds = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Find all outline elements with xmlUrl
        for outline in root.findall(".//outline[@xmlUrl]"):
            title = outline.get("title") or outline.get("text")
            url = outline.get("xmlUrl")
            feeds.append({"title": title, "url": url})
    except Exception as e:
        print(f"Error parsing OPML: {e}")
    return feeds

def verify_feed(feed):
    url = feed['url']
    title = feed['title']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    try:
        # 1. Network Check
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None # Fail
            
        # 2. Content Check
        # Some feeds might return 200 but be empty or html error pages
        d = feedparser.parse(resp.content)
        if d.bozo == 0 or len(d.entries) > 0 or d.feed.get('title'):
             # Determine a robust name
             final_name = d.feed.get('title', title)
             return {"name": final_name, "url": url}
        else:
            return None
            
    except Exception:
        return None

def main():
    print(f"Parsing {OPML_FILE}...")
    feeds = parse_opml(OPML_FILE)
    print(f"Found {len(feeds)} feeds. Verifying availability (this may take a minute)...")
    
    valid_feeds = {}
    
    start_time = time.time()
    completed = 0
    total = len(feeds)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_feed = {executor.submit(verify_feed, feed): feed for feed in feeds}
        
        for future in concurrent.futures.as_completed(future_to_feed):
            completed += 1
            result = future.result()
            if result:
                valid_feeds[result['name']] = result['url']
                print(f"[✅] {result['name']}")
            else:
                pass
                # print(f"[❌] {future_to_feed[future]['title']}")
                
            # Simple progress
            if completed % 10 == 0:
                print(f"Progress: {completed}/{total}")

    duration = time.time() - start_time
    print(f"\nVerification finished in {duration:.2f}s.")
    print(f"Valid Feeds: {len(valid_feeds)} / {total}")
    
    # Save to config
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(valid_feeds, f, indent=4, ensure_ascii=False)
    
    print(f"Updated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
