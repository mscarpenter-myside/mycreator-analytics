
import sys
import json
from src.config import get_config, setup_logging
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES

# Setup
config = get_config()
logger = setup_logging(debug=True)
extractor = MyCreatorExtractor(config)

def probe_reels():
    print("🎬 Probing Reels Analytics...", flush=True)
    
    print(f"Target Workspaces: {[ws['name'] for ws in TARGET_WORKSPACES]}", flush=True)

    reel_id = None
    account_id = None
    workspace_id_found = None

    for ws in TARGET_WORKSPACES:
        print(f"🔎 Checking workspace: {ws['name']}", flush=True)
        ws_id = ws["id"]
        
        url = f"{config.base_url}{config.fetch_plans_endpoint}"
        payload = {
            "workspace_id": ws_id,
            "limit": 40,
            "page": 1,
            "statuses": ["published"],
            "route_name": "list_plans",
            "source": "web",
            "specific_plans": [],
            "labels": [],
            "content_categories": [],
            "automations": [],
            "blog_selection": {},
            "social_selection": {},
            "created_by_members": [],
            "members": [],
            "platformSelection": [], # Leave empty to match extract.py
            "type": [],
            "no_social_account": False,
            "csv_id": "",
            "date_range": ""
        }
        
        resp = extractor._handle_401_and_retry("post", url, json=payload)
        data = resp.json()
        plans = data.get("plans", [])
        
        plan_list = []
        if isinstance(plans, dict) and "data" in plans:
            plan_list = plans["data"]
        elif isinstance(plans, list):
             plan_list = plans
        
        print(f"   Items found: {len(plan_list)}", flush=True)

        for p in plan_list:
            plan_id = p.get("_id") if isinstance(p, dict) else p
            
            # Fetch details
            details = extractor.fetch_plan_details(plan_id, ws_id)
            if not details: continue
            
            for posting in details.get("posting", []):
                p_type = posting.get("published_post_type")
                media_type = posting.get("media_type") 
                
                # Check for ANY video or rich media to see if metrics exist
                if p_type in ["REEL", "VIDEO"] or media_type in ["REEL", "VIDEO", "CAROUSEL_ALBUM"]:
                    reel_id = posting.get("posted_id")
                    if "platform_id" in posting:
                        account_id = posting["platform_id"]
                    elif "account_id" in posting:
                        account_id = posting["account_id"]
                    
                    if reel_id and account_id:
                        print(f"🎯 FOUND {p_type}/{media_type} in {ws['name']}: {reel_id}", flush=True)
                        workspace_id_found = ws_id
                        break
            if reel_id: break
        if reel_id: break
    
    if reel_id and account_id and workspace_id_found:
        print(f"📊 Fetching Analytics for Reel {reel_id}...", flush=True)
        analytics = extractor.fetch_post_analytics(reel_id, workspace_id_found, "instagram", account_id)
        print("--- ANALYTICS DUMP ---", flush=True)
        print(json.dumps(analytics, indent=2), flush=True)
    else:
        print("❌ No Reel found in ANY workspace.", flush=True)


if __name__ == "__main__":
    probe_reels()
