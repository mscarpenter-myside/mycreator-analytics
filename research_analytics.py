import logging
import json
import sys
from src.config import get_config
from src.extract import MyCreatorExtractor
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research_endpoints")

def research_endpoints():
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

    print(f"Using IG IDs: {ig_ids}")

    # Date Range (Last 30 Days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    date_range = f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"

    # Common payload
    payload = {
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

    # Potential Endpoints to Test
    # Based on UI names: "Account insights", "Top post", "Publishing Behavior"
    endpoints_to_test = [
        "/backend/analytics/overview/getGraph", # Check for graphs
        "/backend/analytics/overview/getTopPosts", # Check for top posts
        "/backend/analytics/posts/top",
        "/backend/analytics/engagement/getGraph",
        "/backend/analytics/reach/getGraph",
        "/backend/analytics/impressions/getGraph",
        "/backend/analytics/publishing/behavior", # Guess
        "/backend/analytics/account/insights"     # Guess
    ]

    print("\n--- PROBING ENDPOINTS ---")
    for endpoint in endpoints_to_test:
        url = f"{config.base_url}{endpoint}"
        print(f"Testing {url} ...")
        try:
            resp = extractor._handle_401_and_retry("post", url, json=payload)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"SUCCESS! Keys: {list(data.keys())}")
                # Save sample
                filename = f"resp_{endpoint.split('/')[-1]}.json"
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"Saved to {filename}")
            else:
                print(f"Failed. Response: {resp.text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")
        print("-" * 30)

if __name__ == "__main__":
    research_endpoints()
