
import sys
from src.config import get_config, setup_logging
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES

# Setup
config = get_config()
logger = setup_logging(debug=True)
extractor = MyCreatorExtractor(config)

def probe_guesses():
    print("🔍 Probing Final Guesses...", flush=True)
    
    target_ws = next((ws for ws in TARGET_WORKSPACES if "Florianópolis" in ws["name"]), TARGET_WORKSPACES[0])
    ws_id = target_ws["id"]
    
    # Busca contas para ter o IG ID
    resp = extractor._handle_401_and_retry("post", f"{config.base_url}/backend/fetchSocialAccounts", json={"workspace_id": ws_id})
    ig_id = resp.json().get("instagram", {}).get("accounts", [{}])[0].get("platform_identifier")
    
    if not ig_id:
        print("No IG Account", flush=True)
        return

    payload = {
        "workspace_id": ws_id,
        "date": "2025-01-01 - 2025-02-12",
        "timezone": "America/Sao_Paulo",
        "instagram_accounts": [ig_id],
        "facebook_accounts": [],
        "linkedin_accounts": [],
        "tiktok_accounts": [],
        "twitter_accounts": [],
        "youtube_accounts": [],
        "pinterest_accounts": []
    }
    
    guesses = [
        "/backend/getContentPublishingBehavior",
        "/backend/analytics/getContentPublishingBehavior",
        "/backend/analytics/overview/getContentPublishingBehavior",
        "/backend/analytics/instagram/getContentPublishingBehavior"
    ]
    
    for g in guesses:
        url = f"{config.base_url}{g}"
        print(f"📡 Probing: {g}", flush=True)
        resp = extractor.session.post(url, json=payload, headers=extractor.headers)
        print(f"   Status: {resp.status_code}", flush=True)
        if resp.status_code == 200:
            print(f"   SUCCESS! Response: {resp.text[:500]}", flush=True)

if __name__ == "__main__":
    probe_guesses()
