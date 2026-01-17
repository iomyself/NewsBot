import requests
import json

def load_config():
    try:
        with open('feishu_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def check_auth():
    config = load_config()
    print("--- 1. Getting Tenant Access Token ---")
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": config['app_id'], "app_secret": config['app_secret']}
    
    resp = requests.post(url, json=data)
    print(f"Token Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print("Failed to get token:", resp.text)
        return

    token = resp.json().get("tenant_access_token")
    print(f"Token: {token[:10]}... (Length: {len(token)})")

    print("\n--- 2. Checking Base Info (App Token) ---")
    # API: Get Base Info
    # GET https://open.feishu.cn/open-apis/bitable/v1/apps/:app_token
    base_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{config['app_token']}"
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(base_url, headers=headers)
    print(f"Base Info Status: {resp.status_code}")
    print(f"Response: {resp.text}")

    if resp.json().get('code') != 0:
        print("\n[Diagnosis]")
        print("If code is 91402 (NOTEXIST) here, it confirms the BOT cannot see the BASE.")
        print("Please click 'Share' in the Feishu Doc and add your Bot as editor.")

if __name__ == "__main__":
    check_auth()
