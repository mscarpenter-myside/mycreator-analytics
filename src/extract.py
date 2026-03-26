"""
Módulo de Extração (Extract) do ETL.
Fluxo: Listar -> Preview (Dados JSON) -> Analytics (com Account ID).

Workspaces Alvo (Fixos):
- Florianópolis: 696e75c20f3354d37f074866
- Florianópolis Continente: 696689afcddd41ec6a024adb
- Goiânia: 696689f3c04f3fefdc0118cd
- MyCreator: 68fbfe91e94c0946d103643d
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from dataclasses import dataclass, field

from curl_cffi import requests as curl_requests

from .config import Config

logger = logging.getLogger("mycreator_etl")

# =============================================================================
# WORKSPACES ALVO (FIXOS - Não usar descoberta automática)
# =============================================================================
TARGET_WORKSPACES = [
    {"id": "68fb69151a0869701c0c195c", "name": "MySide"},
    {"id": "68fbf4b9a1a69edd600f0ee7", "name": "Lucrando com Imóveis"},
    {"id": "68fbfe91e94c0946d103643d", "name": "MyCreator"},
    {"id": "696688d158d9e25f340ad964", "name": "Belo Horizonte"},
    {"id": "696689afcddd41ec6a024adb", "name": "Florianópolis Continente"},
    {"id": "696689cc90763878ba06a27b", "name": "Curitiba"},
    {"id": "696689f3c04f3fefdc0118cd", "name": "Goiânia"},
    {"id": "69668a27c14df8f16407dfa9", "name": "Balneário Piçarras"},
    {"id": "696e75c20f3354d37f074866", "name": "Florianópolis"},
    {"id": "696e7742bcec9fe648008357", "name": "Balneário e Itapema"},
]


@dataclass
class PostData:
    """
    Estrutura de dados para um post extraído.
    
    IMPORTANTE: Todos os campos após o primeiro com valor padrão
    também devem ter valores padrão para evitar TypeError.
    """
    # Campos obrigatórios (sem default)
    internal_id: str
    
    # Campos opcionais (com default)
    external_id: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None  # Nome da cidade/workspace
    title: Optional[str] = None
    caption: Optional[str] = None
    platform: Optional[str] = None
    profile_name: Optional[str] = None
    post_type: Optional[str] = None
    media_type: Optional[str] = None  # Tipo de mídia do analytics (Reels, Carousel, Video, etc.)
    published_at: Optional[str] = None
    media_url: Optional[str] = None
    permalink: Optional[str] = None
    follower_count: int = 0  # Seguidores do perfil no momento da extração
    
    # Métricas de Analytics (default = 0)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0
    plays: int = 0
    engagement_rate: float = 0.0
    reach_rate: float = 0.0
    
    # Métricas Avançadas (Reels/Video)
    video_duration: float = 0.0
    total_watch_time: int = 0
    avg_watch_time: float = 0.0
    start_event: int = 0
    
    # Métricas de Stories
    taps_forward: int = 0
    taps_back: int = 0
    exits: int = 0
    replies: int = 0
    
    # Status
    analytics_error: Optional[str] = None
    
    # Rastreabilidade
    extraction_timestamp: Optional[str] = None  # Formato: DD/MM/YYYY HH:MM:SS


@dataclass
class ProfileData:
    """Dados consolidados de um perfil (Instagram, etc)."""
    workspace_name: str
    workspace_id: str
    profile_name: str
    platform_id: str
    platform: str
    followers: int
    posts_count: int
    engagement_total: int
    engagement_rate: float
    reach_total: float
    impressions_total: float
    extraction_timestamp: str


@dataclass
class GeneralProfileData:
    """Dados gerais do perfil (Visão 365 dias/Geral)."""
    workspace_name: str
    workspace_id: str
    profile_summary: str  # Nomes dos perfis agregados
    followers: int
    media_count: int      # Total Posts
    reach_total: float    # Já multiplicado por 1000 se necessário
    impressions_total: float
    engagement_total: int
    engagement_rate: float
    date_range: str
    extraction_timestamp: str


@dataclass
class StoryData:
    """Dados de um Story (Instagram)."""
    internal_id: str
    external_id: str
    workspace_id: str
    workspace_name: str
    profile_name: str
    account_id: str
    published_at: str
    media_url: str
    permalink: str
    
    # Métricas (Se disponível)
    reach: int = 0
    impressions: int = 0
    taps_forward: int = 0
    taps_back: int = 0
    exits: int = 0
    replies: int = 0
    
    extraction_timestamp: Optional[str] = None


class MyCreatorExtractor:
    """
    Extrator de dados da API MyCreator.
    
    Suporta dois modos de autenticação:
    1. Cookie + Token (credenciais manuais)
    2. Email + Password (auto-login via API)
    
    Em caso de erro 401, tenta re-autenticar automaticamente.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.session = curl_requests.Session(impersonate="chrome110")
        self._auth_instance = None
        
        # Inicializa headers base
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": config.base_url,
            "Referer": f"{config.base_url}/planner",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        }
        
        # Configura autenticação
        self._setup_auth()
    
    def _setup_auth(self):
        """Configura autenticação inicial."""
        if self.config.has_valid_session:
            # Usa credenciais existentes
            self.headers["Cookie"] = self.config.cookie
            self.headers["Authorization"] = self.config.authorization_token
            logger.info("🔑 Usando credenciais existentes (Cookie + Token)")
        elif self.config.can_auto_login:
            # Tenta fazer login automático
            logger.info("🔐 Auto-login habilitado, realizando autenticação...")
            self._authenticate()
        else:
            logger.warning("⚠️ Nenhuma credencial configurada!")
    
    def _authenticate(self) -> bool:
        """
        Realiza autenticação via email/password.
        
        Returns:
            bool: True se autenticou com sucesso
        """
        from .auth import MyCreatorAuth
        
        if not self.config.can_auto_login:
            logger.error("❌ Email/Password não configurados para auto-login")
            return False
        
        self._auth_instance = MyCreatorAuth(base_url=self.config.base_url)
        
        if self._auth_instance.authenticate(
            self.config.mycreator_email,
            self.config.mycreator_password
        ):
            # Atualiza headers com novas credenciais
            auth_headers = self._auth_instance.get_auth_headers()
            self.headers.update(auth_headers)
            
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            logger.info(f"✅ Login automático realizado com sucesso!")
            logger.info(f"📅 extraction_timestamp: {timestamp}")
            
            return True
        else:
            logger.error("❌ Falha no login automático")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Garante que o extractor está autenticado.
        
        Returns:
            bool: True se está autenticado
        """
        if "Authorization" in self.headers and self.headers["Authorization"]:
            return True
        
        if self.config.can_auto_login:
            return self._authenticate()
        
        return False
    
    def _handle_401_and_retry(self, method: str, url: str, **kwargs):
        """
        Executa requisição e tenta re-autenticar em caso de 401.
        
        Args:
            method: Método HTTP (get, post)
            url: URL da requisição
            **kwargs: Argumentos adicionais para a requisição
            
        Returns:
            Response ou None
        """
        # Primeira tentativa
        request_func = getattr(self.session, method)
        response = request_func(url, headers=self.headers, **kwargs)
        
        # Se 401 e pode fazer auto-login, tenta re-autenticar
        if response.status_code == 401 and self.config.can_auto_login:
            logger.warning("🔄 Sessão expirada (401), tentando re-autenticar...")
            
            if self._authenticate():
                # Retry com novas credenciais
                response = request_func(url, headers=self.headers, **kwargs)
            else:
                logger.error("❌ Re-autenticação falhou")
        
        return response
    
    # =========================================================================
    # 1. LISTAGEM DE POSTS
    # =========================================================================
    def fetch_posts_list(self, workspace_id: str) -> List[dict]:
        """Busca lista de posts publicados de um workspace específico."""
        url = f"{self.config.base_url}{self.config.fetch_plans_endpoint}"
        
        payload = {
            "workspace_id": workspace_id,
            "limit": self.config.posts_limit,
            "page": 1,
            "statuses": ["published"],
            "sort_column": "post_created_at",
            "order": "descending",
            "route_name": "list_plans",
            "source": "web",
            "specific_plans": [],
            "labels": [],
            "content_categories": [],
            "automations": [],
            "blog_selection": {},
            "social_selection": {},
            "created_by_members": [],
            "members": [],
            "platformSelection": [],
            "type": [],
            "no_social_account": False,
            "csv_id": "",
            "date_range": ""
        }
        
        try:
            response = self._handle_401_and_retry("post", url, json=payload, timeout=30)
            if response.status_code != 200:
                logger.error(f"❌ Erro Listagem: {response.status_code}")
                return []
            data = response.json()
            return data.get("plans", [])
        except Exception as e:
            logger.error(f"❌ Erro na listagem: {e}")
            return []

    # =========================================================================
    # 2. DETALHES DO POST (VIA PREVIEW)
    # =========================================================================
    def fetch_plan_details(self, plan_id: str, workspace_id: str) -> Optional[dict]:
        """Busca detalhes completos de um post via endpoint /backend/plan/preview."""
        url = f"{self.config.base_url}/backend/plan/preview"
        params = {
            "id": plan_id,
            "workspace_id": workspace_id
        }
        
        try:
            resp = self._handle_401_and_retry("get", url, params=params, timeout=60)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return data.get("plan", data)
                except json.JSONDecodeError:
                    return None
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao buscar preview {plan_id}: {e}")
            return None

    # =========================================================================
    # 3. ANALYTICS (COM ACCOUNT_ID OBRIGATÓRIO)
    # =========================================================================
    def fetch_post_analytics(self, posted_id: str, workspace_id: str, platform: str, account_id: str) -> Optional[dict]:
        """
        Busca métricas de analytics de um post.
        
        IMPORTANTE: O account_id é obrigatório para o endpoint funcionar.
        Ele é extraído do campo 'platform_id' dentro do objeto 'posting'.
        """
        url = f"{self.config.base_url}{self.config.analytics_endpoint}"
        if not posted_id or not account_id:
            return None
        
        payload = {
            "id": posted_id,
            "workspace_id": workspace_id,
            "all_post_ids": [posted_id],
            "platforms": platform.lower(),
            "account_id": account_id,
            "date_range": "",
            "labels": [],
            "content_categories": []
        }
        
        try:
            response = self._handle_401_and_retry("post", url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if self._is_valid_analytics(data):
                    return data
        except Exception:
            pass
        return None

    def _is_valid_analytics(self, data) -> bool:
        """Valida se a resposta contém métricas válidas."""
        if not data:
            return False
        
        # Normaliza resposta (pode ser lista ou dict)
        if isinstance(data, list):
            if len(data) == 0:
                return False
            data = data[0]
            
        if isinstance(data, dict):
            metrics = ["likes", "engagement", "reach", "impressions", "comments"]
            return any(k in data for k in metrics)
        return False

    def extract_analytics_metrics(self, analytics) -> dict:
        """Extrai métricas numéricas e tipo de mídia da resposta de analytics."""
        data = analytics
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if not isinstance(data, dict):
            data = {}
        
        return {
            "likes": self._safe_int(data, ["likes", "likeCount", "like_count"]),
            "comments": self._safe_int(data, ["comments", "commentCount", "comment_count"]),
            "shares": self._safe_int(data, ["shares", "shareCount", "share_count"]),
            "saves": self._safe_int(data, ["saves", "saveCount", "save_count", "saved"]),
            "reach": self._safe_int(data, ["reach", "reachCount", "reach_count"]),
            "impressions": self._safe_int(data, ["impressions", "impressionCount", "impression_count"]),
            "plays": self._safe_int(data, ["plays", "videoViews", "views", "video_views"]),
            "media_type": data.get("media_type", ""),
            
            # Métricas Avançadas (Video/Reels)
            "video_duration": data.get("video_duration", 0.0),
            "total_watch_time": self._safe_int(data, ["total_time_watched", "total_watch_time"]),
            "avg_watch_time": data.get("avg_watch_time", 0.0) or data.get("average_watch_time", 0.0),
            
            # Métricas de Stories
            "taps_forward": self._safe_int(data, ["taps_forward", "navigation", "forward"]), # Exemplo, ajustar conforme API real
            "taps_back": self._safe_int(data, ["taps_back", "back"]),
            "exits": self._safe_int(data, ["exits"]),
            "replies": self._safe_int(data, ["replies", "replies_count"]),
        }
    
    def _safe_int(self, data: dict, keys: List[str]) -> int:
        """Extrai valor inteiro de forma segura, tratando formatação."""
        for key in keys:
            if key in data:
                try:
                    val = str(data[key] or 0).replace(",", "").replace(".", "")
                    return int(val)
                except (ValueError, TypeError):
                    continue
        return 0

    # ... (rest of methods) ...


    # =========================================================================
    # FOLLOWER COUNT: via /backend/analytics/overview/getSummary
    # =========================================================================
    def fetch_workspace_follower_counts(self, workspace_id: str) -> dict:
        """
        Busca contagem de seguidores por conta Instagram de um workspace.
        
        Chama getSummary com cada conta individual para obter o follower_count.
        
        Returns:
            Dict mapeando platform_identifier (str) -> {'followers': int, 'name': str}
        """
        follower_map = {}
        
        try:
            # 1. Busca contas Instagram do workspace
            resp = self._handle_401_and_retry(
                "post",
                f"{self.config.base_url}/backend/fetchSocialAccounts",
                json={"workspace_id": workspace_id},
                timeout=15
            )
            if resp.status_code != 200:
                logger.warning(f"⚠️ fetchSocialAccounts falhou: {resp.status_code}")
                return follower_map
            
            social_data = resp.json()
            ig_data = social_data.get("instagram", {})
            ig_accounts = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []
            
            if not ig_accounts:
                return follower_map
            
            # 2. Para cada conta, busca followers via getSummary
            from datetime import datetime, timedelta, timezone as tz
            now = datetime.now(tz(timedelta(hours=-3)))
            end_date = now.strftime("%Y-%m-%d")
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            date_range = f"{start_date} - {end_date}"
            
            for acc in ig_accounts:
                ig_id = str(acc.get("platform_identifier") or acc.get("instagram_id") or "")
                name = acc.get("name", "Unknown")
                
                if not ig_id:
                    continue
                
                payload = {
                    "workspace_id": workspace_id,
                    "date": date_range,
                    "timezone": "America/Sao_Paulo",
                    "facebook_accounts": [],
                    "instagram_accounts": [ig_id],
                    "linkedin_accounts": [],
                    "tiktok_accounts": [],
                    "youtube_accounts": [],
                    "pinterest_accounts": [],
                    "twitter_accounts": [],
                    "gmb_accounts": [],
                    "tumblr_accounts": []
                }
                
                try:
                    resp = self._handle_401_and_retry(
                        "post",
                        f"{self.config.base_url}/backend/analytics/overview/getSummary",
                        json=payload,
                        timeout=10
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        summary = data.get("summary", {})
                        followers = summary.get("followers", 0)
                        follower_map[ig_id] = {
                            "followers": followers,
                            "name": name
                        }
                        logger.info(f"   👤 {name}: {followers:,} seguidores")
                    else:
                        logger.warning(f"   ⚠️ getSummary para {name}: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Erro getSummary {name}: {e}")
                
                time.sleep(0.2)
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar follower counts: {e}")
        
        return follower_map
    
    # =========================================================================
    # ORQUESTRADOR: EXTRAÇÃO DE TODOS OS WORKSPACES
    # =========================================================================
    def extract_from_workspaces(self, workspaces: List[dict] = None) -> List[PostData]:
        """
        Extrai dados de múltiplos workspaces.
        
        Args:
            workspaces: Lista de dicts com 'id' e 'name'. Se None, usa TARGET_WORKSPACES.
            
        Returns:
            Lista consolidada de PostData de todos os workspaces.
        """
        if workspaces is None:
            workspaces = TARGET_WORKSPACES
            
        all_results: List[PostData] = []
        
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws["name"]
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🏙️ WORKSPACE: {ws_name} ({ws_id})")
            logger.info(f"{'='*60}")
            
            results = self._extract_single_workspace(ws_id, ws_name)
            all_results.extend(results)
            
            logger.info(f"✅ {ws_name}: {len(results)} posts extraídos")
            time.sleep(0.5)  # Pausa entre workspaces
        
        logger.info(f"\n🏁 TOTAL GLOBAL: {len(all_results)} posts de {len(workspaces)} workspaces")
        return all_results
    
    def _extract_single_workspace(self, workspace_id: str, workspace_name: str) -> List[PostData]:
        """Extrai todos os posts de um único workspace."""
        results: List[PostData] = []
        
        # 0. Busca follower counts por conta
        logger.info(f"👤 Buscando seguidores dos perfis...")
        follower_map = self.fetch_workspace_follower_counts(workspace_id)
        
        # 1. Busca lista de posts
        plans = self.fetch_posts_list(workspace_id)
        
        if not plans:
            logger.warning(f"⚠️ Nenhum post encontrado em {workspace_name}")
            return results
        
        total = len(plans)
        logger.info(f"📦 Processando {total} posts...")
        
        for i, plan_summary in enumerate(plans, 1):
            internal_id = plan_summary.get("_id")
            
            # 2. Busca detalhes via Preview
            details = self.fetch_plan_details(internal_id, workspace_id)
            if not details:
                continue
            
            # Extrai metadados comuns
            common = details.get("common_sharing_details", {})
            caption = common.get("message", "")
            
            # Título: Prioridade -> title > video.name > multimedia[0].name
            title = common.get("title", "")
            if not title:
                video = common.get("video", {})
                if isinstance(video, dict):
                    title = video.get("name", "")
            if not title:
                multimedia = common.get("multimedia", [])
                if multimedia and isinstance(multimedia, list) and len(multimedia) > 0:
                    first_item = multimedia[0]
                    if isinstance(first_item, dict):
                        title = first_item.get("name", "")
            # Remove extensão de arquivo se presente
            if title and isinstance(title, str) and title.endswith(('.mp4', '.MP4', '.mov', '.MOV')):
                title = title.rsplit('.', 1)[0]
            
            exec_time = details.get("execution_time", {})
            published_at = exec_time.get("date", details.get("updated_at", ""))
            images = common.get("image", [])
            media_url = images[0] if isinstance(images, list) and images else ""
            
            # Itera sobre 'posting' (cada postagem em cada rede)
            postings = details.get("posting", [])
            if not postings:
                continue
                
            for post_item in postings:
                posted_id = post_item.get("posted_id")
                
                # platform_type = Rede Social (Instagram, Facebook, etc)
                platform_type = post_item.get("platform_type", "Instagram")
                
                # published_post_type = Tipo de post (REELS, FEED, STORY)
                published_post_type = post_item.get("published_post_type", "POST")
                
                profile_name = post_item.get("platform", "Unknown")
                permalink = post_item.get("link", "")
                account_id = post_item.get("platform_id")  # Chave para Analytics
                
                # =========================================================================
                # NOVO FILTRO ANTI-GHOSTING BASEADO NO NOME DO PERFIL
                # Como a aba Publisher mantém posts de contas excluídas, a gente
                # varre os nomes ativos do Workspace obtidos pelo fetchSocialAccounts.
                # Se o nome do perfil do post não bater com nenhum ativo, é ignorado.
                # =========================================================================
                active_profile_names = [info["name"].lower() for info in follower_map.values()]
                if profile_name.lower() not in active_profile_names:
                    logger.debug(f"   ⏩ Ignorando post de {profile_name} (Conta não consta mais no Workspace MyCreator)")
                    continue
                
                # Cria objeto PostData com timestamp de extração (horário de Brasília)
                tz_brasilia = timezone(timedelta(hours=-3))
                extraction_ts = datetime.now(tz_brasilia).strftime("%d/%m/%Y %H:%M:%S")
                
                # Busca follower count do perfil deste post
                post_follower_count = 0
                if account_id and str(account_id) in follower_map:
                    post_follower_count = follower_map[str(account_id)]["followers"]
                
                post_data = PostData(
                    internal_id=internal_id,
                    external_id=posted_id,
                    workspace_id=workspace_id,
                    workspace_name=workspace_name,
                    title=title,
                    caption=caption,
                    platform=platform_type,  # Rede Social (Instagram, Facebook)
                    profile_name=profile_name,
                    post_type=published_post_type,  # Tipo de post (REELS, FEED)
                    published_at=published_at,
                    media_url=media_url,
                    permalink=permalink,
                    follower_count=post_follower_count,
                    extraction_timestamp=extraction_ts,
                    media_type=published_post_type
                )
                
                # 3. Busca Analytics
                if posted_id and account_id:
                    analytics = self.fetch_post_analytics(posted_id, workspace_id, platform_type, account_id)
                    
                    if analytics:
                        metrics = self.extract_analytics_metrics(analytics)
                        post_data.likes = metrics["likes"]
                        post_data.comments = metrics["comments"]
                        post_data.shares = metrics["shares"]
                        post_data.saves = metrics["saves"]
                        post_data.reach = metrics["reach"]
                        post_data.impressions = metrics["impressions"]
                        post_data.plays = metrics["plays"]
                        post_data.media_type = metrics.get("media_type") or post_data.media_type
                        
                        # Atribui métricas avançadas
                        post_data.video_duration = float(metrics.get("video_duration", 0.0))
                        post_data.total_watch_time = metrics.get("total_watch_time", 0)
                        post_data.avg_watch_time = float(metrics.get("avg_watch_time", 0.0))
                        
                        post_data.taps_forward = metrics.get("taps_forward", 0)
                        post_data.taps_back = metrics.get("taps_back", 0)
                        post_data.exits = metrics.get("exits", 0)
                        post_data.replies = metrics.get("replies", 0)
                        
                        # Calcula taxas
                        if post_data.reach > 0:
                            engagement = post_data.likes + post_data.saves + post_data.comments + post_data.shares
                            post_data.engagement_rate = round((engagement / post_data.reach), 4)
                            
                            if post_data.follower_count > 0:
                                post_data.reach_rate = round((post_data.reach / post_data.follower_count), 4)
                        
                        logger.info(f"   ✅ [{i}/{total}] {profile_name}: {metrics['likes']} Likes | {metrics['reach']} Reach")
                    else:
                        post_data.analytics_error = "Sem dados"
                else:
                    post_data.analytics_error = "ID ou Conta ausente"
                
                results.append(post_data)
                
            time.sleep(0.3)  # Respeito à API
            
        return results
    
    # =========================================================================
    # EXTRAÇÃO DE STORIES (NOVA ABA)
    # =========================================================================
    def fetch_stories_list(self, workspaces: List[dict] = None) -> List[StoryData]:
        """
        Extrai stories de múltiplos workspaces.
        Usa filtro type=['story'] e busca analytics (se disponível).
        """
        if workspaces is None:
            workspaces = TARGET_WORKSPACES
            
        all_stories: List[StoryData] = []
        from datetime import datetime, timedelta, timezone as tz
        tz_brasilia = tz(timedelta(hours=-3))
        extraction_ts = datetime.now(tz_brasilia).strftime("%d/%m/%Y %H:%M:%S")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📸 INICIANDO EXTRAÇÃO DE STORIES")
        logger.info(f"{'='*60}")
        
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws["name"]
            
            # Reutiliza o endpoint de listagem, mas forçando type=['story']
            url = f"{self.config.base_url}{self.config.fetch_plans_endpoint}"
            payload = {
                "workspace_id": ws_id,
                "limit": self.config.posts_limit, # Usa mesmo limite
                "page": 1,
                "statuses": ["published"],
                "sort_column": "post_created_at",
                "order": "descending",
                "route_name": "list_plans",
                "source": "web",
                "type": ["story"], # FILTRO CHAVE
                "content_categories": [],
                "platformSelection": [],
                "date_range": ""
            }
            
            try:
                # 1. Lista Stories
                resp = self._handle_401_and_retry("post", url, json=payload, timeout=30)
                if resp.status_code != 200:
                    continue
                    
                plans = resp.json().get("plans", [])
                logger.info(f"   📸 {ws_name}: {len(plans)} items (Stories/Reels compartilhados)")
                
                for plan in plans:
                    internal_id = plan.get("_id")
                    
                    # 2. Detalhes
                    details = self.fetch_plan_details(internal_id, ws_id)
                    if not details: continue
                    
                    # Extrai dados básicos
                    postings = details.get("posting", [])
                    exec_time = details.get("execution_time", {})
                    published_at = exec_time.get("date", details.get("updated_at", ""))
                    
                    for p in postings:
                        # Verifica se é story mesmo
                        published_post_type = p.get("published_post_type", "")
                        stories_list = p.get("stories", [])
                        
                        target_ids = []
                        if published_post_type == "STORY":
                             target_ids.append(p.get("posted_id"))
                        
                        # Se foi compartilhado para story (Reel -> Story), pega o ID do story
                        if stories_list:
                            for s in stories_list:
                                if s.get("id"): target_ids.append(s.get("id"))
                                
                        if not target_ids:
                            continue
                            
                        # Para cada story ID identificado
                        for tid in target_ids:
                            if not tid: continue
                            
                            media_url = ""
                            permalink = ""
                            
                            # Tenta achar link/media
                            if stories_list:
                                for s in stories_list:
                                    if s.get("id") == tid:
                                        media_url = s.get("preview", "")
                                        permalink = s.get("link", "")
                                        break
                            
                            if not permalink: permalink = p.get("link", "")
                            
                            story_obj = StoryData(
                                internal_id=internal_id,
                                external_id=tid,
                                workspace_id=ws_id,
                                workspace_name=ws_name,
                                profile_name=p.get("platform", "Unknown"),
                                account_id=p.get("platform_id", ""),
                                published_at=published_at,
                                media_url=media_url,
                                permalink=permalink,
                                extraction_timestamp=extraction_ts
                            )
                            # Analytics (futuro)
                            all_stories.append(story_obj)
                            
            except Exception as e:
                logger.error(f"Erro stories em {ws_name}: {e}")
                
        return all_stories

    # =========================================================================
    # EXTRAÇÃO DE PERFIS (NOVA ABA)
    # =========================================================================
    def extract_profiles(self, workspaces: List[dict] = None) -> List[ProfileData]:
        """
        Extrai dados consolidados de todos os perfis dos workspaces.
        
        Returns:
            Lista de objetos ProfileData para a aba 'Perfis'.
        """
        if workspaces is None:
            workspaces = TARGET_WORKSPACES
            
        all_profiles = []
        
        # ... (implementation would represent code not shown, but we are just defining the interface here effectively by assuming the method continues)
        # Since I can't see the body of extract_profiles in the view_file output (it was truncated), 
        # I will append the NEW methods at the end of the file or after a known block.
        # However, replace_file_content needs context.
        # I will rely on appending to the end of the file if possible or finding a safe spot.
        # The view showed up to line 800 and extract_profiles started at 792.
        # I'll use a known previous method to append AFTER it, or use the class end.
        # Actually I can't see the end of the file.
        # I'll request to see the end of the file first to be safe.
        pass
            
        all_profiles: List[ProfileData] = []
        
        # Timestamp de Brasília
        from datetime import datetime, timedelta, timezone as tz
        tz_brasilia = tz(timedelta(hours=-3))
        extraction_ts = datetime.now(tz_brasilia).strftime("%d/%m/%Y %H:%M:%S")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"👥 INICIANDO EXTRAÇÃO DE PERFIS")
        logger.info(f"{'='*60}")
        
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws["name"]
            
            try:
                # 1. Busca contas Instagram do workspace
                resp = self._handle_401_and_retry(
                    "post",
                    f"{self.config.base_url}/backend/fetchSocialAccounts",
                    json={"workspace_id": ws_id},
                    timeout=15
                )
                
                if resp.status_code != 200:
                    continue
                
                social_data = resp.json()
                ig_data = social_data.get("instagram", {})
                ig_accounts = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []
                
                if not ig_accounts:
                    continue
                
                # 2. Para cada conta, busca detalhes via getSummary
                # Define intervalo de 30 dias para métricas de engajamento
                now = datetime.now(tz_brasilia)
                end_date = now.strftime("%Y-%m-%d")
                start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
                date_range = f"{start_date} - {end_date}"
                
                for acc in ig_accounts:
                    ig_id = str(acc.get("platform_identifier") or acc.get("instagram_id") or "")
                    name = acc.get("name", "Unknown")
                    
                    if not ig_id:
                        continue
                        
                    payload = {
                        "workspace_id": ws_id,
                        "date": date_range,
                        "timezone": "America/Sao_Paulo",
                        "facebook_accounts": [],
                        "instagram_accounts": [ig_id],
                        "linkedin_accounts": [],
                        "tiktok_accounts": [],
                        "youtube_accounts": [],
                        "pinterest_accounts": [],
                        "twitter_accounts": [],
                        "gmb_accounts": [],
                        "tumblr_accounts": []
                    }
                    
                    try:
                        resp_summary = self._handle_401_and_retry(
                            "post",
                            f"{self.config.base_url}/backend/analytics/overview/getSummary",
                            json=payload,
                            timeout=10
                        )
                        
                        followers = 0
                        posts = 0
                        engagement = 0
                        engagement_rate = 0.0
                        reach = 0.0
                        impressions = 0.0
                        
                        if resp_summary.status_code == 200:
                            data = resp_summary.json()
                            summary = data.get("summary", {})
                            followers = summary.get("followers", 0)
                            posts = summary.get("posts", 0)
                            engagement = summary.get("engagement", 0)
                            engagement_rate = summary.get("engagement_rate", 0.0)
                            reach = summary.get("reach", 0.0)
                            impressions = summary.get("impressions", 0.0)
                        
                        profile = ProfileData(
                            workspace_name=ws_name,
                            workspace_id=ws_id,
                            profile_name=name,
                            platform_id=ig_id,
                            platform="Instagram",
                            followers=followers,
                            posts_count=posts,
                            engagement_total=engagement,
                            engagement_rate=engagement_rate,
                            reach_total=reach,
                            impressions_total=impressions,
                            extraction_timestamp=extraction_ts
                        )
                        all_profiles.append(profile)
                        logger.info(f"   👤 {ws_name} -> {name}: {followers} seg.")
                        
                    except Exception as e:
                        logger.error(f"Erro ao extrair perfil {name}: {e}")
                    
                    time.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"Erro ao processar workspace {ws_name} para perfis: {e}")
                
        return all_profiles

    # =========================================================================
    # EXTRAÇÃO DE PERFIS (NOVA ABA)
    # =========================================================================
    def extract_profiles(self, workspaces: List[dict] = None) -> List[ProfileData]:
        """
        Extrai dados consolidados de todos os perfis dos workspaces.
        
        Returns:
            Lista de objetos ProfileData para a aba 'Perfis'.
        """
        if workspaces is None:
            workspaces = TARGET_WORKSPACES
            
        all_profiles: List[ProfileData] = []
        
        # Timestamp de Brasília
        from datetime import datetime, timedelta, timezone as tz
        tz_brasilia = tz(timedelta(hours=-3))
        extraction_ts = datetime.now(tz_brasilia).strftime("%d/%m/%Y %H:%M:%S")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"👥 INICIANDO EXTRAÇÃO DE PERFIS")
        logger.info(f"{'='*60}")
        
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws["name"]
            
            try:
                # 1. Busca contas Instagram do workspace
                resp = self._handle_401_and_retry(
                    "post",
                    f"{self.config.base_url}/backend/fetchSocialAccounts",
                    json={"workspace_id": ws_id},
                    timeout=15
                )
                
                if resp.status_code != 200:
                    continue
                
                social_data = resp.json()
                ig_data = social_data.get("instagram", {})
                ig_accounts = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []
                
                if not ig_accounts:
                    continue
                
                # 2. Para cada conta, busca detalhes via getSummary
                # Define intervalo de 30 dias para métricas de engajamento
                now = datetime.now(tz_brasilia)
                end_date = now.strftime("%Y-%m-%d")
                start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
                date_range = f"{start_date} - {end_date}"
                
                for acc in ig_accounts:
                    ig_id = str(acc.get("platform_identifier") or acc.get("instagram_id") or "")
                    name = acc.get("name", "Unknown")
                    
                    if not ig_id:
                        continue
                        
                    payload = {
                        "workspace_id": ws_id,
                        "date": date_range,
                        "timezone": "America/Sao_Paulo",
                        "facebook_accounts": [],
                        "instagram_accounts": [ig_id],
                        "linkedin_accounts": [],
                        "tiktok_accounts": [],
                        "youtube_accounts": [],
                        "pinterest_accounts": [],
                        "twitter_accounts": [],
                        "gmb_accounts": [],
                        "tumblr_accounts": []
                    }
                    
                    try:
                        resp_summary = self._handle_401_and_retry(
                            "post",
                            f"{self.config.base_url}/backend/analytics/overview/getSummary",
                            json=payload,
                            timeout=10
                        )
                        
                        followers = 0
                        posts = 0
                        engagement = 0
                        engagement_rate = 0.0
                        reach = 0.0
                        impressions = 0.0
                        
                        if resp_summary.status_code == 200:
                            data = resp_summary.json()
                            summary = data.get("summary", {})
                            followers = summary.get("followers", 0)
                            posts = summary.get("posts", 0)
                            engagement = summary.get("engagement", 0)
                            engagement_rate = summary.get("engagement_rate", 0.0)
                            reach = summary.get("reach", 0.0)
                            impressions = summary.get("impressions", 0.0)
                        
                        profile = ProfileData(
                            workspace_name=ws_name,
                            workspace_id=ws_id,
                            profile_name=name,
                            platform_id=ig_id,
                            platform="Instagram",
                            followers=followers,
                            posts_count=posts,
                            engagement_total=engagement,
                            engagement_rate=engagement_rate,
                            reach_total=reach,
                            impressions_total=impressions,
                            extraction_timestamp=extraction_ts
                        )
                        all_profiles.append(profile)
                        logger.info(f"   👤 {ws_name} -> {name}: {followers} seg. ({engagement_rate}% engaj.)")
                        
                    except Exception as e:
                        logger.error(f"Erro ao extrair perfil {name}: {e}")
                    
                    time.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"Erro ao processar workspace {ws_name} para perfis: {e}")
                
        return all_profiles

    # =========================================================================
    # EXTRAÇÃO DE CRESCIMENTO DE SEGUIDORES (audience_growth)
    # =========================================================================
    def extract_audience_growth(self, workspaces: List[dict] = None) -> List[dict]:
        """
        Extrai dados diários de crescimento de seguidores de todos os perfis.
        
        Chama o endpoint /backend/analytics/overview/instagram/audience_growth
        para cada conta Instagram de cada workspace.
        
        Returns:
            Lista de dicts com: data, cidade, perfil, seguidores, variacao_diaria
        """
        if workspaces is None:
            workspaces = TARGET_WORKSPACES
            
        all_rows = []
        
        from datetime import datetime, timedelta, timezone as tz
        tz_brasilia = tz(timedelta(hours=-3))
        now = datetime.now(tz_brasilia)
        end_date = now.strftime("%Y-%m-%d")
        # 60 dias — API retorna zeros além disso
        start_date = (now - timedelta(days=60)).strftime("%Y-%m-%d")
        date_range = f"{start_date} - {end_date}"
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📈 INICIANDO EXTRAÇÃO DE CRESCIMENTO DE SEGUIDORES")
        logger.info(f"📅 Período: {date_range}")
        logger.info(f"{'='*60}")
        
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws["name"]
            
            try:
                # 1. Busca contas Instagram do workspace
                resp = self._handle_401_and_retry(
                    "post",
                    f"{self.config.base_url}/backend/fetchSocialAccounts",
                    json={"workspace_id": ws_id},
                    timeout=15
                )
                
                if resp.status_code != 200:
                    logger.warning(f"⚠️ fetchSocialAccounts falhou para {ws_name}: {resp.status_code}")
                    continue
                
                social_data = resp.json()
                ig_data = social_data.get("instagram", {})
                ig_accounts = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []
                
                if not ig_accounts:
                    logger.warning(f"⚠️ Nenhuma conta IG em {ws_name}")
                    continue
                
                # 2. Para cada conta, busca audience_growth
                for acc in ig_accounts:
                    ig_id = str(acc.get("platform_identifier") or acc.get("instagram_id") or "")
                    name = acc.get("name", "Unknown")
                    
                    if not ig_id:
                        continue
                    
                    payload = {
                        "workspace_id": ws_id,
                        "accounts": [ig_id],
                        "facebook_accounts": [],
                        "twitter_accounts": [],
                        "instagram_accounts": [],
                        "pinterest_accounts": [],
                        "linkedin_accounts": [],
                        "tiktok_accounts": [],
                        "youtube_accounts": [],
                        "date": date_range,
                        "timezone": "America/Sao_Paulo"
                    }
                    
                    try:
                        resp_growth = self._handle_401_and_retry(
                            "post",
                            f"{self.config.base_url}/backend/analytics/overview/instagram/audience_growth",
                            json=payload,
                            timeout=15
                        )
                        
                        if resp_growth.status_code != 200:
                            logger.warning(f"   ⚠️ audience_growth para {name}: {resp_growth.status_code}")
                            continue
                        
                        data = resp_growth.json()
                        overview = data.get("overview", {})
                        growth = overview.get("audience_growth", {})
                        
                        buckets = growth.get("buckets", [])
                        followers = growth.get("followers", [])
                        followers_daily = growth.get("followers_daily", [])
                        
                        if not buckets:
                            logger.warning(f"   ⚠️ Sem dados de crescimento para {name}")
                            continue
                        
                        # Monta linhas (1 por dia) — dados brutos
                        for i, date_str in enumerate(buckets):
                            row = {
                                "data": date_str,
                                "cidade": ws_name,
                                "perfil": name,
                                "seguidores": followers[i] if i < len(followers) else 0,
                                "variacao_diaria": followers_daily[i] if i < len(followers_daily) else 0,
                            }
                            all_rows.append(row)
                        
                        logger.info(f"   📈 {ws_name} → {name}: {len(buckets)} dias de dados")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Erro audience_growth {name}: {e}")
                    
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar workspace {ws_name} para audience_growth: {e}")
        
        logger.info(f"\n📊 Total: {len(all_rows)} registros de crescimento extraídos")
        return all_rows

    # =========================================================================
    # EXTRAÇÃO DE TOP POSTS DA ABA ANALYTICS (posts orgânicos + ContentStudio)
    # =========================================================================
    def fetch_analytics_top_posts(self, workspace_id: str, workspace_name: str,
                                   date_range: str) -> List[dict]:
        """
        Busca top posts da aba Analytics do MyCreator por conta Instagram.

        Endpoint: /backend/analytics/overview/instagram/top_posts
        Chama o endpoint uma vez por conta Instagram do workspace.

        Args:
            workspace_id:   ID do workspace
            workspace_name: Nome do workspace (para rastreabilidade)
            date_range:     Período no formato "YYYY-MM-DD - YYYY-MM-DD"
                            Use "2021-01-01 - {hoje}" para todos os posts.

        Returns:
            Lista de dicts normalizados com dados do post (todas as métricas).
        """
        url = f"{self.config.base_url}/backend/analytics/overview/instagram/top_posts"

        try:
            # 1. Busca contas Instagram do workspace
            resp = self._handle_401_and_retry(
                "post",
                f"{self.config.base_url}/backend/fetchSocialAccounts",
                json={"workspace_id": workspace_id},
                timeout=15
            )
            if resp.status_code != 200:
                logger.warning(f"⚠️ fetchSocialAccounts falhou para {workspace_name}: {resp.status_code}")
                return []

            social_data = resp.json()
            ig_data = social_data.get("instagram", {})
            ig_accounts_raw = ig_data.get("accounts", []) if isinstance(ig_data, dict) else []

            if not ig_accounts_raw:
                logger.warning(f"⚠️ Nenhuma conta IG em {workspace_name}")
                return []

            id_to_name = {}
            for acc in ig_accounts_raw:
                ig_id = str(acc.get("platform_identifier") or acc.get("instagram_id") or "")
                name = acc.get("name", "Unknown")
                if ig_id:
                    id_to_name[ig_id] = name

            if not id_to_name:
                return []

            # 2. Chama /instagram/top_posts uma vez por conta
            all_posts = []
            for ig_id, profile_name in id_to_name.items():
                payload = {
                    "workspace_id": workspace_id,
                    "accounts": [ig_id],
                    "date": date_range,
                    "timezone": "America/Sao_Paulo",
                    "type": "top_posts",
                    "facebook_accounts": [],
                    "instagram_accounts": [],
                    "linkedin_accounts": [],
                    "tiktok_accounts": [],
                    "youtube_accounts": [],
                    "pinterest_accounts": [],
                    "twitter_accounts": [],
                }

                resp = self._handle_401_and_retry("post", url, json=payload, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"⚠️ instagram/top_posts {workspace_name}/{profile_name}: {resp.status_code}")
                    continue

                data = resp.json()
                posts_raw = data if isinstance(data, list) else data.get("data", data.get("posts", []))

                for p in posts_raw:
                    if not isinstance(p, dict):
                        continue

                    media_id = str(
                        p.get("post_id") or p.get("id") or p.get("media_id") or
                        p.get("external_id") or ""
                    )
                    published_at = (
                        p.get("created_time") or p.get("timestamp") or
                        p.get("published_at") or ""
                    )
                    likes        = self._safe_int(p, ["likes", "like_count"])
                    comments     = self._safe_int(p, ["comments", "comments_count", "comment_count"])
                    saves        = self._safe_int(p, ["saves", "saved", "save_count"])
                    shares       = self._safe_int(p, ["shares", "share_count"])
                    reach        = self._safe_int(p, ["reach", "reach_count"])
                    impressions  = self._safe_int(p, ["impressions", "impression_count", "views"])
                    total_eng    = self._safe_int(p, ["total_engagement", "total_interactions", "engagement"])
                    if total_eng == 0:
                        total_eng = likes + comments + saves + shares

                    all_posts.append({
                        "external_id":    media_id,
                        "workspace_name": workspace_name,
                        "profile_name":   profile_name,
                        "published_at":   published_at,
                        "media_type":     p.get("media_type") or p.get("type") or "IMAGE",
                        "caption":        p.get("caption") or p.get("category") or "",
                        "permalink":      p.get("permalink") or p.get("link") or "",
                        "reach":          reach,
                        "impressions":    impressions,
                        "total_engagement": total_eng,
                    })

                time.sleep(0.2)

            logger.debug(f"   📊 {workspace_name}: {len(all_posts)} posts analytics coletados")
            return all_posts

        except Exception as e:
            logger.error(f"❌ Erro em fetch_analytics_top_posts ({workspace_name}): {e}")
            return []