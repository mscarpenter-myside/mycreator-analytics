"""
Script de Força Bruta: Testa variações de payload para obrigar o Analytics a responder.
"""
import logging
import json
from src.config import get_config
from src.extract import MyCreatorExtractor
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")

def brute_force_analytics():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    # DADOS REAIS EXTRAÍDOS DO SEU PREVIEW (Par Perfil + Post que sabemos que existe)
    # Perfil: Cris Carvalho
    PROFILE_ID = "17841401342400767" 
    # Post: Link do Instagram /p/DUS6iu-idKm/
    POST_ID = "17989282301763090"
    WORKSPACE_ID = "696e75c20f3354d37f074866"
    
    url = f"{config.base_url}{config.analytics_endpoint}"
    session = curl_requests.Session(impersonate="chrome110")

    print(f"🥊 Iniciando Round de Testes para Post {POST_ID} (Perfil {PROFILE_ID})")
    
    # VARIAÇÕES DE PAYLOAD PARA TESTAR
    variations = [
        {
            "name": "TENTATIVA 1: account_id",
            "payload": {
                "id": POST_ID,
                "workspace_id": WORKSPACE_ID,
                "all_post_ids": [POST_ID],
                "platforms": "instagram",
                "account_id": PROFILE_ID,  # <--- Adicionando conta
                "date_range": ""
            }
        },
        {
            "name": "TENTATIVA 2: social_profile_id",
            "payload": {
                "id": POST_ID,
                "workspace_id": WORKSPACE_ID,
                "all_post_ids": [POST_ID],
                "platforms": "instagram",
                "social_profile_id": PROFILE_ID, # <--- Outro nome comum
                "date_range": ""
            }
        },
        {
            "name": "TENTATIVA 3: profile_id",
            "payload": {
                "id": POST_ID,
                "workspace_id": WORKSPACE_ID,
                "all_post_ids": [POST_ID],
                "platforms": "instagram",
                "profile_id": PROFILE_ID,
                "date_range": ""
            }
        },
        {
            "name": "TENTATIVA 4: platforms como Lista",
            "payload": {
                "id": POST_ID,
                "workspace_id": WORKSPACE_ID,
                "all_post_ids": [POST_ID],
                "platforms": ["instagram"], # <--- Lista
                "date_range": ""
            }
        },
        {
            "name": "TENTATIVA 5: Capitalized",
            "payload": {
                "id": POST_ID,
                "workspace_id": WORKSPACE_ID,
                "all_post_ids": [POST_ID],
                "platforms": "Instagram", # <--- Maiúscula
                "date_range": ""
            }
        },
        {
            "name": "TENTATIVA 6: Payload Mínimo + Conta",
            "payload": {
                "id": POST_ID,
                "workspace_id": WORKSPACE_ID,
                "account_id": PROFILE_ID,
                "platforms": "instagram"
            }
        }
    ]

    for test in variations:
        print(f"\n👉 {test['name']}...")
        try:
            resp = session.post(url, headers=extractor.headers, json=test['payload'], timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Verifica se veio dados (não vazio)
                if str(data) != "[]":
                    print(f"   🎉 SUCESSO! O servidor respondeu:")
                    print(json.dumps(data, indent=2))
                    return # Para no primeiro sucesso
                else:
                    print("   ⚠️ Resposta vazia []")
            else:
                print(f"   ❌ Status {resp.status_code}")
        except Exception as e:
            print(f"   💥 Erro: {e}")

    print("\n🏁 Fim dos testes.")

if __name__ == "__main__":
    brute_force_analytics()