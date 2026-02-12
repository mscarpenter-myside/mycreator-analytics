#!/usr/bin/env python3
"""
Smart probe: tenta descobrir o endpoint de analytics overview do ContentStudio/MyCreator.
Baseado na screenshot: Analytics > Overview mostra Followers, Posts, Engagements, etc.
Tenta variações de date format e account_id format.
"""
import json
import time
from src.config import get_config
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES

def log(msg): print(msg, flush=True)

def probe():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    ws_id = TARGET_WORKSPACES[0]["id"]
    base_url = config.base_url
    
    # Primeiro, buscar todos os account_ids do workspace
    resp = extractor.session.post(
        f"{base_url}/backend/fetchSocialAccounts",
        headers=extractor.headers,
        json={"workspace_id": ws_id},
        timeout=15
    )
    social_data = resp.json()
    
    # Extrair todos os Instagram account IDs
    ig_data = social_data.get("instagram", {})
    ig_accounts = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []
    
    account_ids = []
    for acc in ig_accounts:
        aid = acc.get("instagram_id") or acc.get("platform_identifier")
        if aid:
            account_ids.append(str(aid))
    
    internal_ids = [acc.get("_id") for acc in ig_accounts if acc.get("_id")]
    
    log(f"Workspace: {ws_id}")
    log(f"Instagram Account IDs: {account_ids}")
    log(f"Internal IDs: {internal_ids}")
    log(f"Total: {len(account_ids)} contas")
    
    # Formatos de date range que ContentStudio pode usar
    date_formats = [
        "Jan 13, 2026 - Feb 12, 2026",
        "2026-01-13 - 2026-02-12",
        {"start_date": "2026-01-13", "end_date": "2026-02-12"},
        "last_30_days",
        "30days",
        "",
    ]
    
    # Endpoints candidatos (baseados na estrutura do ContentStudio)
    base_paths = [
        "/backend/analytics/instagram/getOverviewAnalytics",
        "/backend/analytics/instagram/getOverviewV2",
        "/backend/analytics/instagram/getOverview",
        "/backend/analytics/instagram/overview",
        "/backend/analytics/getOverviewAnalytics",
        "/backend/analytics/overview",
        "/backend/analytics/instagram/getSummaryAnalytics",
        "/backend/analytics/instagram/getSummary",
        "/backend/analytics/instagram/getAccountAnalytics",
        "/backend/analytics/getInstagramOverview",
        "/backend/analytics/instagram/getTopCards",
        "/backend/analytics/instagram/getCards",
        "/backend/analytics/instagram/getStats",
        "/backend/analytics/campaignLabelAnalytics/getOverviewAnalytics",
        "/backend/analytics/campaignLabelAnalytics/getOverview",
    ]
    
    # Variações de payloads
    def make_payloads(path, ws_id, account_ids, internal_ids):
        payloads = []
        
        # Com date como string "Jan 13, 2026 - Feb 12, 2026"
        payloads.append({
            "workspace_id": ws_id,
            "date": "Jan 13, 2026 - Feb 12, 2026",
            "instagram_account_id": account_ids,
            "type": "instagram"
        })
        
        # Com date como string range e accounts como array
        payloads.append({
            "workspace_id": ws_id,
            "date": "Jan 13, 2026 - Feb 12, 2026",
            "accounts": account_ids,
            "type": "instagram"
        })
        
        # Com date_range e account_ids
        payloads.append({
            "workspace_id": ws_id,
            "date_range": "Jan 13, 2026 - Feb 12, 2026",
            "account_ids": account_ids,
            "platform": "instagram"
        })
        
        # Com single account_id (primeiro)
        if account_ids:
            payloads.append({
                "workspace_id": ws_id,
                "date": "Jan 13, 2026 - Feb 12, 2026",
                "instagram_account_id": account_ids[0],
                "type": "instagram"
            })
        
        # Com internal _id
        if internal_ids:
            payloads.append({
                "workspace_id": ws_id,
                "date": "Jan 13, 2026 - Feb 12, 2026",
                "instagram_account_id": internal_ids[0],
                "type": "instagram"
            })
        
        # Sem tipo, só workspace + date
        payloads.append({
            "workspace_id": ws_id,
            "date": "Jan 13, 2026 - Feb 12, 2026",
        })
        
        # Com ISO dates
        payloads.append({
            "workspace_id": ws_id,
            "start_date": "2026-01-13",
            "end_date": "2026-02-12",
            "instagram_account_id": account_ids,
            "type": "instagram"
        })
        
        # last_30_days
        payloads.append({
            "workspace_id": ws_id,
            "date_range": "last_30_days",
            "instagram_account_id": account_ids,
            "type": "instagram"
        })
        
        return payloads
    
    found_endpoints = []
    
    for path in base_paths:
        url = f"{base_url}{path}"
        payloads = make_payloads(path, ws_id, account_ids, internal_ids)
        
        for pi, payload in enumerate(payloads):
            try:
                resp = extractor.session.post(url, headers=extractor.headers, json=payload, timeout=10)
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)[:3000]
                        log(f"\n✅ POST {path} (payload #{pi}) -> 200")
                        log(f"Payload: {json.dumps(payload, ensure_ascii=False, default=str)[:200]}")
                        log(f"Response:\n{data_str}")
                        found_endpoints.append({"path": path, "payload_index": pi, "payload": payload})
                        break  # Found working payload for this path
                    except:
                        log(f"✅ POST {path} (#{pi}) -> 200 (non-JSON)")
                elif resp.status_code not in (404, 405, 500):
                    # Interesting status codes (400, 401, 422 etc)
                    try:
                        err = resp.json()
                        err_str = json.dumps(err, ensure_ascii=False, default=str)[:300]
                        log(f"⚠️ POST {path} (#{pi}) -> {resp.status_code}: {err_str}")
                    except:
                        pass
            except Exception as e:
                pass
            
            time.sleep(0.15)
        time.sleep(0.2)
    
    # =========================================================================
    # EXTRA: Tenta o mesmo padrão do getPlannerAnalytics mas para account
    # =========================================================================
    log(f"\n{'='*70}")
    log("Tentando padrões baseados em getPlannerAnalytics...")
    log(f"{'='*70}")
    
    analytics_base = "/backend/analytics/campaignLabelAnalytics"
    extra_paths = [
        f"{analytics_base}/getOverviewAnalytics",
        f"{analytics_base}/getAccountOverviewAnalytics",
        f"{analytics_base}/getInstagramOverview",
        f"{analytics_base}/getInstagramAnalytics",
        f"{analytics_base}/getAccountSummary",
        f"{analytics_base}/getFollowersCount",
        f"{analytics_base}/getFollowers",
        f"{analytics_base}/getTopCardsAnalytics",
        f"{analytics_base}/getTopCards",
    ]
    
    for path in extra_paths:
        url = f"{base_url}{path}"
        for payload in [
            {"workspace_id": ws_id, "date": "Jan 13, 2026 - Feb 12, 2026", "instagram_account_id": account_ids, "type": "instagram"},
            {"workspace_id": ws_id, "date": "Jan 13, 2026 - Feb 12, 2026", "instagram_account_id": account_ids[0] if account_ids else "", "type": "instagram"},
            {"workspace_id": ws_id, "date": "Jan 13, 2026 - Feb 12, 2026", "account_id": account_ids[0] if account_ids else "", "platform": "instagram"},
        ]:
            try:
                resp = extractor.session.post(url, headers=extractor.headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)[:3000]
                    log(f"\n✅ POST {path} -> 200")
                    log(f"Payload: {json.dumps(payload, ensure_ascii=False, default=str)[:200]}")
                    log(f"Response:\n{data_str}")
                    found_endpoints.append({"path": path, "payload": payload})
                    break
                elif resp.status_code not in (404, 405, 500):
                    try:
                        err_str = json.dumps(resp.json(), ensure_ascii=False, default=str)[:300]
                        log(f"⚠️ POST {path} -> {resp.status_code}: {err_str}")
                    except:
                        pass
            except:
                pass
            time.sleep(0.15)
    
    # =========================================================================
    # EXTRA 2: Tenta buscar o JS bundle para encontrar rotas
    # =========================================================================
    log(f"\n{'='*70}")
    log("Buscando rotas na pagina HTML/JS...")
    log(f"{'='*70}")
    
    try:
        resp = extractor.session.get(
            f"{base_url}/analytics/instagram/overview",
            headers={**extractor.headers, "Accept": "text/html,application/xhtml+xml"},
            timeout=15
        )
        if resp.status_code == 200:
            html = resp.text
            # Look for API routes in the HTML
            import re
            # Find JS bundle URLs
            js_urls = re.findall(r'src="(/js/[^"]+)"', html)
            log(f"JS bundles encontrados: {len(js_urls)}")
            for js_url in js_urls[:3]:
                log(f"  {js_url}")
            
            # Check for analytics-related strings in HTML
            analytics_patterns = re.findall(r'analytics[^"\']*(?:overview|follower|account|stats)[^"\']*', html, re.IGNORECASE)
            if analytics_patterns:
                log(f"Padrões analytics encontrados no HTML: {analytics_patterns[:10]}")
    except Exception as e:
        log(f"Erro ao buscar HTML: {e}")
    
    log(f"\n{'='*70}")
    log(f"RESUMO: {len(found_endpoints)} endpoints encontrados")
    for ep in found_endpoints:
        log(f"  {ep['path']}")
    log(f"{'='*70}")


if __name__ == "__main__":
    probe()
