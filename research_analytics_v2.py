import logging
import json
import sys
from src.config import get_config
from src.extract import MyCreatorExtractor
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research_endpoints")

def research_endpoints_v2():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    # Florianópolis Workspace ID
    workspace_id = "696e75c20f3354d37f074866"
    
    # Authenticate to get accounts
    url_accounts = f"{config.base_url}/backend/fetchSocialAccounts"
    resp = extractor._handle_401_and_retry("post", url_accounts, json={"workspace_id": workspace_id})
    if resp.status_code != 200:
        print("Failed to fetch accounts")
        return

    accounts_data = resp.json()
    ig_accounts = accounts_data.get("instagram", {}).get("accounts", [])
    ig_ids = [str(acc.get("platform_identifier") or acc.get("instagram_id")) for acc in ig_accounts if acc.get("platform_identifier")]
    
    if not ig_ids:
        print("No IG accounts")
        return

    # Date Range (Last 30 Days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    date_range = f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"

    # Base payload
    base_payload = {
        "workspace_id": workspace_id,
        "date": date_range,
        "timezone": "America/Sao_Paulo",
        "instagram_accounts": ig_ids,
        "facebook_accounts": [],
        "linkedin_accounts": [],
        "tiktok_accounts": [],
        "youtube_accounts": [],
        "pinterest_accounts": [],
        "twitter_accounts": [],
        "gmb_accounts": [],
        "tumblr_accounts": []
    }

    # Test getTopPosts with variations
    print("\n--- TESTING getTopPosts ---")
    
    variations = [
        {"sortBy": "reach", "limit": 5},
        {"sortBy": "engagement", "limit": 5},
        {"metric": "reach", "limit": 5},
        {"sort": "reach"},
        {"type": "reach"},
        {} # Original
    ]
    
    url = f"{config.base_url}/backend/analytics/overview/getTopPosts"
    
    for v in variations:
        payload = base_payload.copy()
        payload.update(v)
        print(f"Testing with extra params: {v}")
        try:
            resp = extractor._handle_401_and_retry("post", url, json=payload)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("SUCCESS!")
                print(json.dumps(resp.json(), indent=2)[:500])
                break
            else:
                print(f"Failed. {resp.text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")
        print("-" * 20)
        
    # Test other potential endpoints with basic payload
    print("\n--- TESTING OTHER ENDPOINTS ---")
    other_endpoints = [
        "/backend/analytics/overview/getEngagementGraph", # Common pattern
        "/backend/analytics/overview/getReachGraph",
        "/backend/analytics/overview/getImpressionsGraph",
        "/backend/analytics/overview/getPublishingBehavior",
        "/backend/analytics/account/getInsights",
        "/backend/analytics/getAccountInsights",
        "/backend/analytics/posts/getTop",
        "/backend/analytics/top-posts"
    ]
    
    for endpoint in other_endpoints:
        url = f"{config.base_url}{endpoint}"
        print(f"Testing {url} ...")
        resp = extractor._handle_401_and_retry("post", url, json=base_payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
             print("SUCCESS!")
             print(json.dumps(resp.json(), indent=2)[:500])

if __name__ == "__main__":
    research_endpoints_v2()
