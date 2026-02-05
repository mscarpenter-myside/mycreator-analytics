"""
Script Sniffer: Testa a chamada de Analytics com um ID REAL da sua planilha.
"""
import logging
import json
from src.config import get_config
from src.extract import MyCreatorExtractor
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")

def debug_raw():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    # ---------------------------------------------------------
    # DADOS DA SUA PLANILHA (LINHA 0)
    # ---------------------------------------------------------
    TEST_POST_ID = "18121605679564481"  # ID Externo extraído
    WORKSPACE_ID = "696e75c20f3354d37f074866"
    PLATFORM = "instagram" 
    
    url = f"{config.base_url}{config.analytics_endpoint}"
    
    # Payload EXATO do extract.py
    payload = {
        "id": TEST_POST_ID,
        "workspace_id": WORKSPACE_ID,
        "all_post_ids": [TEST_POST_ID],
        "platforms": PLATFORM, # Testaremos variações aqui se falhar
        "date_range": "",
        "labels": [],
        "content_categories": []
    }
    
    print(f"🎯 Disparando Analytics para Post ID: {TEST_POST_ID}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    session = curl_requests.Session(impersonate="chrome110")
    
    try:
        resp = session.post(url, headers=extractor.headers, json=payload, timeout=15)
        print(f"\n🚦 STATUS: {resp.status_code}")
        print("-" * 40)
        print("📄 RESPOSTA CRUA DO SERVIDOR:")
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
        print("-" * 40)
        
    except Exception as e:
        print(f"💥 Erro: {e}")

if __name__ == "__main__":
    debug_raw()