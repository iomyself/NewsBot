import requests
import json
import os

def load_config():
    try:
        with open('feishu_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def get_tenant_access_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": app_id, "app_secret": app_secret}
    res = requests.post(url, json=data).json()
    return res.get("tenant_access_token")

def list_tables():
    config = load_config()
    token = get_tenant_access_token(config['app_id'], config['app_secret'])
    if not token: return

    # API to list tables
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{config['app_token']}/tables"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Fetching Tables for App Token: {config['app_token']}...")
    resp = requests.get(url, headers=headers)
    print("Response Status:", resp.status_code)
    
    try:
        data = resp.json()
        if data.get('code') == 0:
            print("\n=== Available Tables ===")
            for table in data['data']['items']:
                print(f"Name: {table['name']}, Table ID: {table['table_id']}")
            print("========================\n")
        else:
            print("Error listing tables:", data)
            print("Possible Cause: User forgot to add Bot as collaborator to the Doc?")
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    list_tables()
