"""
Script de Prova Final: Testa Analytics usando o ID INTERNO (_id).
"""
import logging
import json
from src.config import get_config
from src.extract import MyCreatorExtractor
from curl_cffi import requests as curl_requests

# Configura logs
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("final_debug")

def test_internal_id_analytics():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    print("📡 1. Buscando um post real para pegar o ID correto...")
    posts = extractor.fetch_posts_list()
    
    if not posts:
        print("❌ Nenhum post encontrado.")
        return

    # Pega o primeiro post
    post = posts[0]
    INTERNAL_ID = post.get("_id")
    # Pega a plataforma dinamicamente ou fallback para instagram
    acc_sel = post.get("account_selection", {})
    PLATFORM = "instagram"
    if isinstance(acc_sel, dict) and list(acc_sel.keys()):
        PLATFORM = list(acc_sel.keys())[0]

    print(f"🎯 ALVO ENCONTRADO:")
    print(f"   ID Interno (_id): {INTERNAL_ID}")
    print(f"   Plataforma: {PLATFORM}")
    print("-" * 50)

    # MONTA O PAYLOAD CORRETO COM O ID INTERNO
    url = f"{config.base_url}{config.analytics_endpoint}"
    
    payload = {
        "id": INTERNAL_ID,                # <--- AQUI ESTÁ A MUDANÇA
        "workspace_id": "696e75c20f3354d37f074866",
        "all_post_ids": [INTERNAL_ID],    # <--- E AQUI TAMBÉM
        "platforms": PLATFORM,
        "date_range": "",
        "labels": [],
        "content_categories": []
    }

    print(f"📡 2. Enviando requisição de Analytics para ID INTERNO...")
    
    session = curl_requests.Session(impersonate="chrome110")
    headers = extractor.headers # Reusa headers do extrator

    try:
        response = session.post(url, headers=headers, json=payload, timeout=15)
        print(f"🚦 STATUS: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📦 RESPOSTA DO SERVIDOR:")
            print(json.dumps(data, indent=2))
            
            # Verifica se veio recheio
            if isinstance(data, list) and len(data) > 0:
                print("\n✅ VITÓRIA! O ARRAY NÃO ESTÁ VAZIO!")
            elif isinstance(data, dict) and "likes" in str(data):
                print("\n✅ VITÓRIA! DADOS ENCONTRADOS!")
            else:
                print("\n⚠️ Ainda vazio... O mistério continua.")
        else:
            print(f"❌ ERRO: {response.text[:200]}")
            
    except Exception as e:
        print(f"💥 EXCEÇÃO: {e}")

if __name__ == "__main__":
    test_internal_id_analytics()
    