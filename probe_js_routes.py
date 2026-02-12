#!/usr/bin/env python3
"""
Targeted search: download the largest app JS chunks and find /backend/ API routes.
Focus on analytics-related routes.
"""
import json
import re
from src.config import get_config
from src.extract import MyCreatorExtractor

def log(msg): print(msg, flush=True)

def main():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    base_url = config.base_url
    
    # Fetch the analytics page to get chunk URLs
    resp = extractor.session.get(
        f"{base_url}/analytics",
        headers={**extractor.headers, "Accept": "text/html"},
        timeout=15
    )
    html = resp.text
    
    # Extract all JS chunk references
    all_js = re.findall(r'(?:src|href)="(/[^"]*\.js[^"]*)"', html)
    log(f"Total JS files referenced: {len(all_js)}")
    
    # Also find dynamically referenced chunks
    chunk_refs = re.findall(r'"(/(?:app|vendors)-[^"]+\.js)"', html)
    
    all_routes = set()
    analytics_routes = set()
    follower_routes = set()
    
    # Focus on app-*.js files (they contain business logic)
    app_files = [f for f in all_js if '/app-' in f]
    log(f"App JS files: {len(app_files)}")
    
    for i, js_path in enumerate(app_files):
        url = f"{base_url}{js_path}"
        try:
            resp = extractor.session.get(url, headers=extractor.headers, timeout=15)
            if resp.status_code == 200:
                js = resp.text
                
                # Find all /backend/ routes
                routes = re.findall(r'["\'](/backend/[^"\']{5,120})["\']', js)
                for r in routes:
                    # Clean up template literals
                    r_clean = r.split('"+')[0].split("'+")[0]
                    all_routes.add(r_clean)
                    
                    if 'analytics' in r_clean.lower():
                        analytics_routes.add(r_clean)
                    if 'follower' in r_clean.lower():
                        follower_routes.add(r_clean)
                
                # Also search for concatenated routes with variables
                concat_routes = re.findall(r'["\'](/backend/analytics/[^"\']*)["\']', js)
                for r in concat_routes:
                    analytics_routes.add(r)
                
                # Search for 'followers' or 'follower' in any context
                if 'follower' in js.lower():
                    # Get surrounding context
                    for m in re.finditer(r'follower', js, re.IGNORECASE):
                        start = max(0, m.start() - 100)
                        end = min(len(js), m.end() + 100)
                        context = js[start:end].replace('\n', ' ')
                        follower_routes.add(f"[context in {js_path}]: {context}")
                
                if routes:
                    log(f"  [{i+1}/{len(app_files)}] {js_path}: {len(routes)} routes found")
        except Exception as e:
            pass
    
    # Print results
    log(f"\n{'='*70}")
    log(f"ALL /backend/ routes found: {len(all_routes)}")
    log(f"{'='*70}")
    for r in sorted(all_routes):
        log(f"  {r}")
    
    log(f"\n{'='*70}")
    log(f"ANALYTICS routes: {len(analytics_routes)}")
    log(f"{'='*70}")
    for r in sorted(analytics_routes):
        log(f"  {r}")
    
    log(f"\n{'='*70}")
    log(f"FOLLOWER mentions: {len(follower_routes)}")
    log(f"{'='*70}")
    for r in sorted(follower_routes):
        log(f"  {r}")
    
    # Save full results
    with open("/tmp/mycreator_routes.json", "w") as f:
        json.dump({
            "all_routes": sorted(all_routes),
            "analytics_routes": sorted(analytics_routes),
            "follower_mentions": sorted(follower_routes)
        }, f, indent=2, ensure_ascii=False)
    
    log(f"\nSalvo em /tmp/mycreator_routes.json")

if __name__ == "__main__":
    main()
