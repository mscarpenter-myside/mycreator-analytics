"""
Script de Debug - Reprodução Mínima da Requisição de Analytics
Objetivo: Isolar a requisição que está falhando com HTTP 500
"""

import json
from curl_cffi import requests as curl_requests

# Importa config para pegar credenciais do .env
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import get_config

def main():
    print("=" * 60)
    print("🔬 DEBUG - Requisição de Analytics")
    print("=" * 60)
    
    # Carrega credenciais
    config = get_config()
    
    # URL completa do endpoint
    url = f"{config.base_url}/backend/analytics/campaignLabelAnalytics/getPlannerAnalytics"
    print(f"\n📍 URL: {url}")
    
    # Headers replicando Chrome (idêntico ao DevTools)
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Cookie": config.cookie,
        "Authorization": config.authorization_token,
        "Origin": config.base_url,
        "Referer": f"{config.base_url}/planner",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    }
    
    # Payload EXATO do DevTools (que funcionou no navegador)
    payload = {
        "id": "17841401342400767",
        "workspace_id": "696e75c20f3354d37f074866",
        "all_post_ids": ["17841401342400767"],
        "platforms": "instagram",
        "date_range": "",
        "labels": [],
        "content_categories": []
    }
    
    print(f"\n📦 Payload:")
    print(json.dumps(payload, indent=2))
    
    print(f"\n🔐 Cookie (primeiros 50 chars): {config.cookie[:50]}...")
    print(f"🔑 Token: {config.authorization_token[:30]}...")
    
    # Faz a requisição com curl_cffi (bypass TLS fingerprint)
    print("\n" + "-" * 60)
    print("📡 Enviando requisição...")
    print("-" * 60)
    
    try:
        session = curl_requests.Session(impersonate="chrome110")
        
        response = session.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        print(f"\n✅ Status Code: {response.status_code}")
        print(f"📏 Content-Length: {len(response.text)} bytes")
        print(f"📋 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("📄 RESPONSE BODY (completo):")
        print("=" * 60)
        print(response.text)
        
        # Tenta parsear como JSON
        try:
            data = response.json()
            print("\n" + "=" * 60)
            print("🔍 JSON Parseado:")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        except json.JSONDecodeError:
            print("\n⚠️ Resposta não é JSON válido")
            
    except Exception as e:
        print(f"\n❌ EXCEÇÃO: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
