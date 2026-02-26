import sys
from pathlib import Path

# Adiciona o diretório principal ao path para importar src
sys.path.append(str(Path(__file__).parent.parent))

from src.config import get_config, setup_logging
from src.extract import MyCreatorExtractor

# Configura logger
logger = setup_logging(debug=False)

def run_sync():
    """Executa a sincronização de dados (triggerJob) para todas as contas."""
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    logger.info("=======================================")
    logger.info("🚀 INICIANDO SINCRONIZAÇÃO DE DADOS 🚀")
    logger.info("=======================================")
    
    # 1. Obter os workspaces configurados
    from src.extract import TARGET_WORKSPACES
    workspaces = TARGET_WORKSPACES
    
    for ws in workspaces:
        ws_id = ws["id"]
        ws_name = ws["name"]
        
        logger.info(f"\n🏙️ Sincronizando Workspace: {ws_name} ({ws_id})")
        
        try:
            # 2. Buscar contas sociais do workspace para pegar o account_id
            url_accounts = f"{config.base_url}/backend/fetchSocialAccounts"
            payload_accounts = {"workspace_id": ws_id}
            
            resp_accounts = extractor._handle_401_and_retry("post", url_accounts, json=payload_accounts, timeout=15)
            if resp_accounts.status_code != 200:
                logger.warning(f"⚠️ Falha ao buscar contas para {ws_name}: {resp_accounts.status_code}")
                continue
                
            social_data = resp_accounts.json()
            
            # Contas do Instagram
            ig_data = social_data.get("instagram", {})
            ig_accounts = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []
            
            # Contas do Facebook (se necessário)
            # fb_data = social_data.get("facebook", {})
            # fb_accounts = fb_data.get("accounts", []) if isinstance(fb_data, dict) else []
            
            # Por enquanto, foca no Instagram baseado no payload do usuário
            all_accounts_to_sync = []
            
            for acc in ig_accounts:
                account_id = acc.get("_id")
                if account_id:
                    all_accounts_to_sync.append(("instagram", account_id, acc.get("name", "Unknown IG")))
                    
            if not all_accounts_to_sync:
                logger.info(f"   ℹ️ Nenhuma conta do Instagram encontrada para sincronizar em {ws_name}")
                continue
                
            # 3. Disparar triggerJob para cada conta
            url_sync = f"{config.base_url}/backend/api/analytics/triggerJob"
            
            for platform, account_id, account_name in all_accounts_to_sync:
                payload_sync = {
                    "workspace_id": ws_id,
                    "account_id": account_id,
                    "platform": platform
                }
                
                logger.info(f"   🔄 Disparando sync para {account_name} ({platform})...")
                
                resp_sync = extractor._handle_401_and_retry("post", url_sync, json=payload_sync, timeout=15)
                
                if resp_sync.status_code == 200:
                    try:
                        resp_json = resp_sync.json()
                        if resp_json.get("status") is True:
                            logger.info(f"   ✅ Sincronização disparada com sucesso para {account_name}")
                        else:
                            logger.warning(f"   ⚠️ Falha na sincronização para {account_name} (API retornou status false): {resp_json}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Sincronização retornou 200 mas o JSON é inválido: {resp_sync.text}")
                else:
                    logger.warning(f"   ⚠️ Falha na sincronização para {account_name}: {resp_sync.status_code} - {resp_sync.text}")
                    
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar workspace {ws_name}: {e}")

    logger.info("\n🏁 SINCRONIZAÇÃO CONCLUÍDA 🏁")

if __name__ == "__main__":
    run_sync()
