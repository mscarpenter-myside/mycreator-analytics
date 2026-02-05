"""
Configurações centralizadas do ETL MyCreator Analytics.

Este módulo gerencia todas as credenciais e configurações,
lendo de variáveis de ambiente (para produção/GitHub Actions)
ou de um arquivo .env (para desenvolvimento local).
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Tenta carregar .env apenas se existir (desenvolvimento local)
try:
    from dotenv import load_dotenv
    
    # Carrega .env do diretório raiz do projeto
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Variáveis carregadas de: {env_path}")
except ImportError:
    pass  # python-dotenv não instalado, usa apenas env vars


@dataclass
class Config:
    """Configurações do ETL."""
    
    # Credenciais MyCreator (opção 1: Cookie + Token)
    cookie: str
    authorization_token: str
    
    # Credenciais MyCreator (opção 2: Email + Password para auto-login)
    mycreator_email: str
    mycreator_password: str
    
    # Google Sheets
    google_sheet_id: str
    sheet_tab_name: str
    gcp_credentials: Optional[dict]
    
    # Configurações de execução
    posts_limit: int
    write_mode: str  # "overwrite" ou "append"
    debug_mode: bool
    
    # URLs da API MyCreator
    base_url: str = "https://mycreator.myside.com.br"
    fetch_plans_endpoint: str = "/backend/fetchPlans"
    analytics_endpoint: str = "/backend/analytics/campaignLabelAnalytics/getPlannerAnalytics"
    
    def __post_init__(self):
        """Validações após inicialização."""
        # Valida que tem pelo menos uma forma de autenticação
        has_cookie_auth = bool(self.cookie and self.authorization_token)
        has_email_auth = bool(self.mycreator_email and self.mycreator_password)
        
        if not has_cookie_auth and not has_email_auth:
            raise ValueError(
                "❌ Credenciais insuficientes! Configure:\n"
                "   - MYCREATOR_COOKIE + MYCREATOR_TOKEN, ou\n"
                "   - MYCREATOR_EMAIL + MYCREATOR_PASSWORD"
            )
        
        if self.write_mode not in ("overwrite", "append"):
            raise ValueError(f"❌ WRITE_MODE inválido: {self.write_mode}")
        
        # Garante formato correto do token
        if self.authorization_token and not self.authorization_token.startswith("Bearer "):
            object.__setattr__(self, 'authorization_token', f"Bearer {self.authorization_token}")
    
    @property
    def can_auto_login(self) -> bool:
        """Verifica se pode fazer login automático."""
        return bool(self.mycreator_email and self.mycreator_password)
    
    @property
    def has_valid_session(self) -> bool:
        """Verifica se tem sessão válida (cookie + token)."""
        return bool(self.cookie and self.authorization_token)

def load_gcp_credentials() -> Optional[dict]:
    """
    Carrega credenciais do Google Cloud de múltiplas fontes.
    
    Prioridade:
    1. Variável de ambiente GCP_SA_KEY (GitHub Actions)
    2. Arquivo credentials/service_account.json (desenvolvimento local)
    
    Returns:
        dict: Credenciais JSON parseadas
        None: Se não encontrar credenciais
    """
    # 1. Tenta ler de variável de ambiente (GitHub Actions)
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key:
        try:
            credentials = json.loads(gcp_sa_key)
            logging.info("✅ Credenciais GCP carregadas de GCP_SA_KEY")
            return credentials
        except json.JSONDecodeError as e:
            logging.error(f"❌ Erro ao parsear GCP_SA_KEY: {e}")
            raise
    
    # 2. Tenta ler de arquivo local
    cred_path = Path(__file__).parent.parent / "credentials" / "service_account.json"
    if cred_path.exists():
        try:
            with open(cred_path, "r", encoding="utf-8") as f:
                credentials = json.load(f)
            logging.info(f"✅ Credenciais GCP carregadas de: {cred_path}")
            return credentials
        except json.JSONDecodeError as e:
            logging.error(f"❌ Erro ao parsear {cred_path}: {e}")
            raise
    
    logging.warning("⚠️ Credenciais GCP não encontradas!")
    return None


def get_config() -> Config:
    """
    Carrega e retorna a configuração completa.
    
    Returns:
        Config: Objeto de configuração validado
    """
    return Config(
        # Credenciais MyCreator (Cookie + Token)
        cookie=os.environ.get("MYCREATOR_COOKIE", ""),
        authorization_token=os.environ.get("MYCREATOR_TOKEN", ""),
        
        # Credenciais MyCreator (Email + Password)
        mycreator_email=os.environ.get("MYCREATOR_EMAIL", ""),
        mycreator_password=os.environ.get("MYCREATOR_PASSWORD", ""),
        
        # Google Sheets
        google_sheet_id=os.environ.get("GOOGLE_SHEET_ID", ""),
        sheet_tab_name=os.environ.get("SHEET_TAB_NAME", "Dados_Brutos"),
        gcp_credentials=load_gcp_credentials(),
        
        # Configurações de execução
        posts_limit=int(os.environ.get("POSTS_LIMIT", "50")),
        write_mode=os.environ.get("WRITE_MODE", "overwrite"),
        debug_mode=os.environ.get("DEBUG_MODE", "false").lower() == "true",
    )


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configura o sistema de logging.
    
    Args:
        debug: Se True, usa nível DEBUG, senão INFO
        
    Returns:
        Logger: Logger configurado
    """
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("mycreator_etl")
