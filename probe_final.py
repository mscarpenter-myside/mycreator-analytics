#!/usr/bin/env python3
"""
getSummary works! But returns aggregated follower count per workspace.
Need: per-account follower count.
Test: call getSummary with ONE account at a time to get individual counts.
"""
import json
from src.config import get_config
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES

def log(msg): print(msg, flush=True)

def main():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    base_url = config.base_url
    ws_id = TARGET_WORKSPACES[0]["id"]  # Florianópolis
    
    # Get accounts
    resp = extractor.session.post(
        f"{base_url}/backend/fetchSocialAccounts",
        headers=extractor.headers,
        json={"workspace_id": ws_id},
        timeout=15
    )
    ig_accounts = resp.json().get("instagram", {}).get("accounts", [])
    
    log(f"Testing per-account follower count for Florianópolis ({len(ig_accounts)} accounts)\n")
    
    total_individual = 0
    for acc in ig_accounts:
        ig_id = str(acc.get("platform_identifier") or acc.get("instagram_id"))
        name = acc.get("name")
        
        payload = {
            "workspace_id": ws_id,
            "date": "2026-01-13 - 2026-02-12",
            "timezone": "America/Sao_Paulo",
            "facebook_accounts": [],
            "instagram_accounts": [ig_id],  # Single account!
            "linkedin_accounts": [],
            "tiktok_accounts": [],
            "youtube_accounts": [],
            "pinterest_accounts": [],
            "twitter_accounts": [],
            "gmb_accounts": [],
            "tumblr_accounts": []
        }
        
        resp = extractor.session.post(
            f"{base_url}/backend/analytics/overview/getSummary",
            headers={**extractor.headers, "Accept": "application/json", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        
        if resp.status_code == 200:
            data = resp.json()
            summary = data.get("summary", {})
            followers = summary.get("followers", 0)
            total_individual += followers
            log(f"  {name}: {followers} followers | {summary.get('posts', 0)} posts | {summary.get('engagement', 0)} engagements")
        else:
            log(f"  {name}: ERROR {resp.status_code}")
    
    log(f"\nTotal individual: {total_individual}")
    log(f"Total aggregated: 8162")
    log(f"Match: {'✅' if total_individual == 8162 else '❌'}")

if __name__ == "__main__":
    main()
