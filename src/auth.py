"""
Módulo de Autenticação MyCreator.

Realiza login automático na plataforma MyCreator usando email/password,
captura Cookie e Bearer Token para uso nas requisições da API.

Usa curl_cffi para personificação de navegador e evitar bloqueios WAF.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from curl_cffi import requests as curl_requests

logger = logging.getLogger("mycreator_etl")


class MyCreatorAuth:
    """
    Gerenciador de autenticação MyCreator.
    
    Realiza login via API e mantém as credenciais atualizadas.
    """
    
    # Endpoint de login (identificado no tráfego do site)
    LOGIN_ENDPOINT = "/backend/auth/login"
    
    def __init__(
        self, 
        base_url: str = "https://mycreator.myside.com.br",
        impersonate: str = "chrome110"
    ):
        """
        Inicializa o autenticador.
        
        Args:
            base_url: URL base da API MyCreator
            impersonate: Versão do Chrome para personificação (curl_cffi)
        """
        self.base_url = base_url
        self.session = curl_requests.Session(impersonate=impersonate)
        
        # Credenciais obtidas após login
        self._cookie: Optional[str] = None
        self._token: Optional[str] = None
        self._authenticated: bool = False
        self._auth_timestamp: Optional[str] = None
    
    @property
    def cookie(self) -> Optional[str]:
        """Cookie de sessão."""
        return self._cookie
    
    @property
    def token(self) -> Optional[str]:
        """Bearer token de autorização."""
        return self._token
    
    @property
    def is_authenticated(self) -> bool:
        """Verifica se está autenticado."""
        return self._authenticated and self._token is not None
    
    def authenticate(self, email: str, password: str) -> bool:
        """
        Realiza login no MyCreator.
        
        Args:
            email: Email do usuário
            password: Senha do usuário
            
        Returns:
            bool: True se autenticou com sucesso
        """
        url = f"{self.base_url}{self.LOGIN_ENDPOINT}"
        
        payload = {
            "email": email,
            "password": password,
            "remember_me": True
        }
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        }
        
        try:
            logger.info("🔐 Tentando autenticar no MyCreator...")
            
            response = self.session.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                return self._process_auth_response(response)
            elif response.status_code == 401:
                logger.error("❌ Credenciais inválidas (401)")
                return False
            elif response.status_code == 403:
                logger.error("❌ Acesso negado (403) - possível bloqueio WAF")
                return False
            else:
                logger.error(f"❌ Erro de autenticação: {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            logger.exception(f"❌ Erro ao autenticar: {e}")
            return False
    
    def _process_auth_response(self, response) -> bool:
        """
        Processa a resposta de autenticação e extrai credenciais.
        
        Args:
            response: Resposta HTTP do login
            
        Returns:
            bool: True se extraiu credenciais com sucesso
        """
        try:
            # Extrai cookies da resposta
            cookies = response.cookies
            cookie_parts = []
            for name, value in cookies.items():
                cookie_parts.append(f"{name}={value}")
            
            if cookie_parts:
                self._cookie = "; ".join(cookie_parts)
            
            # Extrai token do JSON de resposta
            data = response.json()
            
            # Tenta diferentes estruturas do JSON
            token = None
            if isinstance(data, dict):
                # Estrutura 1: { "token": "xxx" }
                token = data.get("token")
                
                # Estrutura 2: { "data": { "token": "xxx" } }
                if not token and "data" in data:
                    token = data["data"].get("token")
                
                # Estrutura 3: { "access_token": "xxx" }
                if not token:
                    token = data.get("access_token")
                
                # Estrutura 4: { "user": { "token": "xxx" } }
                if not token and "user" in data:
                    token = data["user"].get("token")
            
            if token:
                self._token = f"Bearer {token}" if not token.startswith("Bearer") else token
                self._authenticated = True
                self._auth_timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
                logger.info(f"✅ Autenticação bem-sucedida!")
                logger.info(f"📅 Timestamp: {self._auth_timestamp}")
                logger.debug(f"🔑 Token obtido: {self._token[:50]}...")
                
                return True
            else:
                # Se não encontrou token no JSON, tenta no header
                auth_header = response.headers.get("Authorization")
                if auth_header:
                    self._token = auth_header
                    self._authenticated = True
                    self._auth_timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    logger.info(f"✅ Autenticação bem-sucedida (token no header)!")
                    return True
                
                logger.warning("⚠️ Login OK mas token não encontrado na resposta")
                logger.debug(f"Response JSON: {data}")
                return False
                
        except Exception as e:
            logger.exception(f"❌ Erro ao processar resposta de auth: {e}")
            return False
    
    def get_auth_headers(self) -> dict:
        """
        Retorna headers de autenticação para usar em requisições.
        
        Returns:
            dict: Headers com Cookie e Authorization
        """
        headers = {}
        
        if self._cookie:
            headers["Cookie"] = self._cookie
        
        if self._token:
            headers["Authorization"] = self._token
        
        return headers
    
    def refresh_if_needed(self, email: str, password: str) -> bool:
        """
        Re-autentica se necessário.
        
        Args:
            email: Email do usuário
            password: Senha do usuário
            
        Returns:
            bool: True se está autenticado (já estava ou re-autenticou)
        """
        if self.is_authenticated:
            return True
        
        logger.info("🔄 Sessão expirada, re-autenticando...")
        return self.authenticate(email, password)
    
    def invalidate(self):
        """Invalida a sessão atual."""
        self._cookie = None
        self._token = None
        self._authenticated = False
        self._auth_timestamp = None
        logger.info("🔓 Sessão invalidada")


def authenticate_mycreator(email: str, password: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Função helper para autenticar e obter credenciais.
    
    Args:
        email: Email do usuário
        password: Senha do usuário
        
    Returns:
        Tuple[cookie, token]: Credenciais ou (None, None) se falhou
    """
    auth = MyCreatorAuth()
    
    if auth.authenticate(email, password):
        return auth.cookie, auth.token
    
    return None, None
