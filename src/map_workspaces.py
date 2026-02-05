"""
Script para Mapear Workspaces (Cidades) disponíveis na conta.
"""
import logging
import json
from src.config import get_config
from src.extract import MyCreatorExtractor
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")

def map_workspaces():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    session = curl_requests.Session(impersonate="chrome110")
    
    print("🌍 Iniciando Mapeamento de Workspaces (Cidades)...")
    
    # Tentativa nos endpoints mais comuns de perfil/equipe
    endpoints = [
        "/backend/api/users/auth_user", # Geralmente traz tudo do usuário
        "/backend/workspaces",
        "/backend/team/workspaces",
        "/backend/users/me"
    ]
    
    found = False
    
    for endpoint in endpoints:
        url = f"{config.base_url}{endpoint}"
        try:
            resp = session.get(url, headers=extractor.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                
                # Procura pela lista de workspaces/teams dentro da resposta
                # A estrutura costuma ser: user -> workspaces OU user -> team -> workspaces
                workspaces = []
                
                # Varredura genérica por listas que pareçam workspaces
                s_data = json.dumps(data)
                if "workspaces" in data:
                    workspaces = data["workspaces"]
                elif "user" in data and "workspaces" in data["user"]:
                    workspaces = data["user"]["workspaces"]
                elif "data" in data and isinstance(data["data"], list):
                    workspaces = data["data"] # As vezes o endpoint é direto
                
                if workspaces:
                    print(f"\n✅ SUCESSO via {endpoint}!")
                    print(f"   Encontrados {len(workspaces)} workspaces.\n")
                    
                    print(f"{'ID':<30} | {'NOME DA CIDADE/WORKSPACE'}")
                    print("-" * 60)
                    
                    for ws in workspaces:
                        w_id = ws.get("_id", ws.get("id", "N/A"))
                        w_name = ws.get("name", ws.get("title", "Sem Nome"))
                        print(f"{w_id:<30} | {w_name}")
                        
                    found = True
                    break
        except Exception as e:
            pass
            
    if not found:
        print("\n❌ Não consegui listar automaticamente. ")
        print("   Por favor, abra o DevTools, troque de cidade e copie a resposta da requisição 'auth_user' ou 'workspaces'.")

if __name__ == "__main__":
    map_workspaces()