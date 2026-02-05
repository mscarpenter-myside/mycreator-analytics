"""
Script Caça-JSON: Testa endpoints POST para achar onde estão os DADOS brutos.
"""
import logging
import json
from src.config import get_config
from src.extract import MyCreatorExtractor
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")

def hunt_json_api():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    # 1. Busca um ID real
    print("📡 Buscando ID válido...")
    posts = extractor.fetch_posts_list()
    if not posts: return
    
    test_id = posts[0].get("_id")
    print(f"🔑 ID Alvo: {test_id}")
    
    session = curl_requests.Session(impersonate="chrome110")
    
    # LISTA DE POSSÍVEIS ENDPOINTS DE API (Muitos usam POST)
    candidates = [
        # O mais provável (baseado no JSON que você viu antes)
        "/backend/planner/getPlan",       
        "/backend/planner/get-plan",
        "/backend/planner/plans/get",
        "/backend/planner/details",
        # Variações REST que as vezes aceitam POST para 'read'
        f"/backend/planner/plans/{test_id}",
        "/backend/posts/get",
        # API do Publisher
        "/publisher/planner/getPlan"
    ]
    
    print(f"🔫 Disparando contra {len(candidates)} endpoints de API...")
    
    # Payload padrão para requisições POST
    payloads = [
        {"id": test_id},
        {"plan_id": test_id},
        {"post_id": test_id}
    ]

    for url_suffix in candidates:
        url = f"{config.base_url}{url_suffix}"
        
        for payload in payloads:
            try:
                # Tenta POST
                resp = session.post(url, headers=extractor.headers, json=payload, timeout=5)
                
                # Só nos interessa se for SUCESSO (200) e JSON
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        # Verifica se é o JSON rico que queremos (tem a chave 'plan' ou 'posting'?)
                        s_data = json.dumps(data)
                        if "posting" in s_data or "platform_id" in s_data:
                            print(f"\n🎉 BINGO! ACHAMOS A API DE DADOS!")
                            print(f"   URL: {url_suffix}")
                            print(f"   Payload que funcionou: {payload}")
                            print(f"   Conteúdo (resumo): {s_data[:100]}...")
                            return # Encerra a busca
                        else:
                            print(f"   ⚠️ {url_suffix}: 200 OK (JSON), mas parece vazio/genérico.")
                    except:
                        # Se der erro de decode, era HTML disfarçado
                        pass
                
            except Exception:
                pass
                
        print(f"   ❌ {url_suffix} não retornou dados úteis.")

    print("\n🏁 Fim da varredura.")

if __name__ == "__main__":
    hunt_json_api()