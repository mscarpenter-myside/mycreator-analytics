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
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field

from curl_cffi import requests as curl_requests

from .config import Config

logger = logging.getLogger("mycreator_etl")

# =============================================================================
# WORKSPACES ALVO (FIXOS - Não usar descoberta automática)
# =============================================================================
TARGET_WORKSPACES = [
    {"id": "696e75c20f3354d37f074866", "name": "Florianópolis"},
    {"id": "696689afcddd41ec6a024adb", "name": "Florianópolis Continente"},
    {"id": "696689f3c04f3fefdc0118cd", "name": "Goiânia"},
    {"id": "68fbfe91e94c0946d103643d", "name": "MyCreator"},
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
    published_at: Optional[str] = None
    media_url: Optional[str] = None
    permalink: Optional[str] = None
    
    # Métricas de Analytics (default = 0)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0
    plays: int = 0
    engagement_rate: float = 0.0
    
    # Status
    analytics_error: Optional[str] = None
    
    # Rastreabilidade
    extraction_timestamp: Optional[str] = None  # Formato: DD/MM/YYYY HH:MM:SS


class MyCreatorExtractor:
    
    def __init__(self, config: Config):
        self.config = config
        self.session = curl_requests.Session(impersonate="chrome110")
        
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Cookie": config.cookie,
            "Authorization": config.authorization_token,
            "Origin": config.base_url,
            "Referer": f"{config.base_url}/planner",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        }
    
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
            response = self.session.post(url, headers=self.headers, json=payload, timeout=30)
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
            resp = self.session.get(url, headers=self.headers, params=params, timeout=15)
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
            response = self.session.post(url, headers=self.headers, json=payload, timeout=10)
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
        """Extrai métricas numéricas da resposta de analytics."""
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
                
                # Cria objeto PostData com timestamp de extração
                extraction_ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
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
                    extraction_timestamp=extraction_ts
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
                        
                        # Calcula taxa de engajamento
                        if post_data.reach > 0:
                            engagement = post_data.likes + post_data.saves + post_data.comments
                            post_data.engagement_rate = round((engagement / post_data.reach) * 100, 2)
                        
                        logger.info(f"   ✅ [{i}/{total}] {profile_name}: {metrics['likes']} Likes | {metrics['reach']} Reach")
                    else:
                        post_data.analytics_error = "Sem dados"
                else:
                    post_data.analytics_error = "ID ou Conta ausente"
                
                results.append(post_data)
                
            time.sleep(0.3)  # Respeito à API
            
        return results
    
    # Mantém método legado para compatibilidade
    def extract_all(self) -> List[PostData]:
        """Método legado - redireciona para extract_from_workspaces."""
        return self.extract_from_workspaces()