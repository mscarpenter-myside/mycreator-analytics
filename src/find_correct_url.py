"""
Script para descobrir a URL correta de Detalhes do Post.
"""
import logging
from src.config import get_config
from src.extract import MyCreatorExtractor
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")

def find_url():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    # 1. Pega um ID real para testar
    print("📡 Buscando um ID válido...")
    posts = extractor.fetch_posts_list()
    if not posts: return
    
    # Pega o ID do primeiro post da lista
    test_id = posts[0].get("_id")
    print(f"🔑 ID Alvo: {test_id}")
    
    session = curl_requests.Session(impersonate="chrome110")
    
    # 2. Lista de Endpoints para testar (Focados em 'Edit' e 'Show')
    candidates = [
        # O mais provável para abrir modal de edição
        f"/backend/planner/plans/{test_id}/edit", 
        f"/backend/planner/plans/{test_id}/show",
        f"/backend/planner/plan/{test_id}",
        # Variações de API
        f"/backend/api/plans/{test_id}",
        f"/backend/posts/{test_id}",
        # Tenta rota de edição do Publisher (as vezes o backend responde aqui)
        f"/publisher/planner/plans/{test_id}/edit" 
    ]
    
    print(f"🔫 Testando {len(candidates)} URLs...")
    
    found = False
    for url in candidates:
        full_url = f"{config.base_url}{url}"
        try:
            resp = session.get(full_url, headers=extractor.headers, timeout=5)
            print(f"   👉 {url} : Status {resp.status_code}")
            
            if resp.status_code == 200:
                print(f"\n✅ ACHAMOS! A URL correta é: {url}")
                print("   (Copie essa URL para usar no extract.py)")
                found = True
                break
        except Exception as e:
            print(f"   ❌ Erro: {e}")

    if not found:
        print("\n⚠️ Nenhuma URL GET funcionou. Pode ser um POST.")
        # Teste rápido de POST
        post_url = f"{config.base_url}/backend/planner/getPlan"
        resp = session.post(post_url, headers=extractor.headers, json={"id": test_id})
        print(f"   👉 POST {post_url} : Status {resp.status_code}")

if __name__ == "__main__":
    find_url()