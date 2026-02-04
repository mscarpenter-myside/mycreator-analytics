"""
Módulo de Extração (Extract) do ETL.

Responsável por fazer requisições à API da MyCreator usando curl_cffi
para bypass de proteções WAF/Cloudflare através de TLS fingerprinting.
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass

from curl_cffi import requests as curl_requests

from .config import Config

logger = logging.getLogger("mycreator_etl")


@dataclass
class PostData:
    """Estrutura de dados de um post extraído."""
    internal_id: str
    external_id: Optional[str]
    title: Optional[str]
    caption: Optional[str]
    platform: Optional[str]
    post_type: Optional[str]
    published_at: Optional[str]
    media_url: Optional[str]
    permalink: Optional[str]
    
    # Métricas de Analytics
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0
    plays: int = 0  # Para vídeos/reels
    
    # Métricas calculadas
    engagement_rate: float = 0.0
    
    # Status
    analytics_error: Optional[str] = None


class MyCreatorExtractor:
    """
    Extrator de dados da plataforma MyCreator.
    
    Usa curl_cffi com impersonate para simular um navegador Chrome
    e evitar bloqueios de WAF/Cloudflare.
    """
    
    def __init__(self, config: Config):
        """
        Inicializa o extrator.
        
        Args:
            config: Configurações do ETL
        """
        self.config = config
        self.session = curl_requests.Session(impersonate="chrome110")
        
        # Headers padrão
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Cookie": config.cookie,
            "Authorization": config.authorization_token,
            "Origin": config.base_url,
            "Referer": f"{config.base_url}/planner",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }
    
    def fetch_posts_list(self) -> list[dict]:
        """
        Busca a lista de posts publicados via endpoint fetchPlans.
        
        Returns:
            list[dict]: Lista de posts em formato raw (JSON da API)
        """
        url = f"{self.config.base_url}{self.config.fetch_plans_endpoint}"
        
        # Payload para buscar posts publicados
        payload = {
            "status": "published",
            "limit": self.config.posts_limit,
            "offset": 0,
            "orderBy": "publishedAt",
            "orderDirection": "desc",
        }
        
        logger.info(f"📡 Buscando últimos {self.config.posts_limit} posts publicados...")
        logger.debug(f"URL: {url}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = self.session.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            logger.debug(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Erro na requisição: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return []
            
            data = response.json()
            
            # Debug: Salva estrutura do JSON para análise
            if self.config.debug_mode:
                self._dump_json_structure(data, "fetch_plans_response.json")
            
            # Extrai lista de posts (a estrutura pode variar)
            posts = self._extract_posts_from_response(data)
            
            logger.info(f"✅ Encontrados {len(posts)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"❌ Exceção ao buscar posts: {e}")
            return []
    
    def _extract_posts_from_response(self, data: dict) -> list[dict]:
        """
        Extrai lista de posts da resposta da API.
        
        A estrutura pode variar, então tentamos múltiplos caminhos.
        
        Args:
            data: JSON da resposta
            
        Returns:
            list[dict]: Lista de posts
        """
        # Tenta diferentes estruturas comuns de API
        possible_paths = [
            data.get("data", []),
            data.get("posts", []),
            data.get("plans", []),
            data.get("items", []),
            data.get("results", []),
            data if isinstance(data, list) else [],
        ]
        
        for posts in possible_paths:
            if isinstance(posts, list) and len(posts) > 0:
                return posts
        
        # Se não encontrou, loga a estrutura para debug
        logger.warning("⚠️ Estrutura de resposta não reconhecida")
        if self.config.debug_mode:
            logger.debug(f"Keys disponíveis: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        
        return []
    
    def find_external_id(self, post: dict) -> Optional[str]:
        """
        Busca o external_id (ID da plataforma, ex: Instagram) no JSON do post.
        
        O external_id pode estar em diferentes locais dependendo da estrutura.
        Esta função faz uma busca profunda no JSON.
        
        Args:
            post: Dicionário do post
            
        Returns:
            str: external_id se encontrado, None caso contrário
        """
        # Caminhos conhecidos onde o external_id pode estar
        known_paths = [
            "externalId",
            "external_id",
            "platformId",
            "platform_id",
            "igMediaId",
            "ig_media_id",
            "mediaId",
            "media_id",
            "instagramId",
            "instagram_id",
            "postId",
            "post_id",
        ]
        
        # Busca direta no nível raiz
        for key in known_paths:
            if key in post and post[key]:
                logger.debug(f"External ID encontrado em '{key}': {post[key]}")
                return str(post[key])
        
        # Busca em objetos aninhados comuns
        nested_objects = ["media", "instagram", "platform", "socialPost", "publishedPost"]
        for obj_name in nested_objects:
            if obj_name in post and isinstance(post[obj_name], dict):
                for key in known_paths:
                    if key in post[obj_name] and post[obj_name][key]:
                        logger.debug(f"External ID encontrado em '{obj_name}.{key}': {post[obj_name][key]}")
                        return str(post[obj_name][key])
        
        # Busca recursiva em todo o JSON
        external_id = self._deep_search_key(post, known_paths)
        if external_id:
            return str(external_id)
        
        # Não encontrou - loga para debug
        if self.config.debug_mode:
            logger.warning(f"⚠️ External ID não encontrado para post")
            self._log_post_structure(post)
        
        return None
    
    def _deep_search_key(self, obj: any, keys: list[str], depth: int = 0, max_depth: int = 5) -> Optional[str]:
        """
        Busca recursiva por chaves no JSON.
        
        Args:
            obj: Objeto a ser pesquisado
            keys: Lista de chaves a procurar
            depth: Profundidade atual
            max_depth: Profundidade máxima
            
        Returns:
            Valor encontrado ou None
        """
        if depth > max_depth:
            return None
        
        if isinstance(obj, dict):
            for key in keys:
                if key in obj and obj[key]:
                    return obj[key]
            
            for value in obj.values():
                result = self._deep_search_key(value, keys, depth + 1, max_depth)
                if result:
                    return result
        
        elif isinstance(obj, list):
            for item in obj:
                result = self._deep_search_key(item, keys, depth + 1, max_depth)
                if result:
                    return result
        
        return None
    
    def _log_post_structure(self, post: dict, indent: int = 2):
        """Loga a estrutura do post para debug."""
        def get_structure(obj, depth=0, max_depth=3):
            if depth > max_depth:
                return "..."
            
            if isinstance(obj, dict):
                return {k: get_structure(v, depth + 1) for k, v in list(obj.items())[:10]}
            elif isinstance(obj, list):
                return [get_structure(obj[0], depth + 1)] if obj else []
            else:
                return type(obj).__name__
        
        structure = get_structure(post)
        logger.debug(f"Estrutura do post:\n{json.dumps(structure, indent=indent)}")
    
    def fetch_post_analytics(self, post_id: str, is_external: bool = True) -> Optional[dict]:
        """
        Busca analytics de um post específico.
        
        Args:
            post_id: ID do post (external ou internal)
            is_external: Se True, usa external_id, senão internal_id
            
        Returns:
            dict: Dados de analytics ou None se falhar
        """
        url = f"{self.config.base_url}{self.config.analytics_endpoint}"
        
        # O payload pode variar - tentamos diferentes estruturas
        payloads_to_try = [
            {"postId": post_id},
            {"externalId": post_id},
            {"mediaId": post_id},
            {"id": post_id},
            {"planId": post_id},
        ]
        
        for payload in payloads_to_try:
            try:
                response = self.session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verifica se a resposta contém dados válidos
                    if self._is_valid_analytics(data):
                        logger.debug(f"✅ Analytics encontrado com payload: {payload}")
                        return data
                
            except Exception as e:
                logger.debug(f"Tentativa falhou com payload {payload}: {e}")
                continue
        
        return None
    
    def _is_valid_analytics(self, data: dict) -> bool:
        """Verifica se a resposta contém dados de analytics válidos."""
        if not data:
            return False
        
        # Verifica se tem campos típicos de analytics
        analytics_fields = ["likes", "comments", "reach", "impressions", "saves", "plays"]
        
        for field in analytics_fields:
            if field in data or (isinstance(data.get("data"), dict) and field in data["data"]):
                return True
        
        return False
    
    def extract_analytics_metrics(self, analytics: dict) -> dict:
        """
        Extrai métricas do JSON de analytics.
        
        Args:
            analytics: JSON de analytics da API
            
        Returns:
            dict: Métricas extraídas
        """
        # Pode estar aninhado em "data"
        data = analytics.get("data", analytics)
        
        return {
            "likes": self._safe_int(data, ["likes", "likeCount", "like_count"]),
            "comments": self._safe_int(data, ["comments", "commentCount", "comment_count"]),
            "shares": self._safe_int(data, ["shares", "shareCount", "share_count"]),
            "saves": self._safe_int(data, ["saves", "saveCount", "save_count", "saved"]),
            "reach": self._safe_int(data, ["reach", "reachCount", "reach_count"]),
            "impressions": self._safe_int(data, ["impressions", "impressionCount", "impression_count"]),
            "plays": self._safe_int(data, ["plays", "videoViews", "video_views", "views"]),
        }
    
    def _safe_int(self, data: dict, keys: list[str]) -> int:
        """Extrai valor inteiro de múltiplas chaves possíveis."""
        for key in keys:
            if key in data:
                try:
                    return int(data[key] or 0)
                except (ValueError, TypeError):
                    continue
        return 0
    
    def extract_post_metadata(self, post: dict) -> dict:
        """
        Extrai metadados de um post.
        
        Args:
            post: JSON do post
            
        Returns:
            dict: Metadados extraídos
        """
        return {
            "internal_id": str(post.get("id", post.get("_id", post.get("planId", "")))),
            "title": post.get("title", post.get("name", "")),
            "caption": post.get("caption", post.get("description", post.get("content", ""))),
            "platform": post.get("platform", post.get("socialNetwork", post.get("network", ""))),
            "post_type": post.get("type", post.get("mediaType", post.get("postType", ""))),
            "published_at": post.get("publishedAt", post.get("published_at", post.get("createdAt", ""))),
            "media_url": self._extract_media_url(post),
            "permalink": post.get("permalink", post.get("url", post.get("link", ""))),
        }
    
    def _extract_media_url(self, post: dict) -> str:
        """Extrai URL da mídia do post."""
        # Tenta diferentes caminhos
        media_paths = [
            post.get("mediaUrl"),
            post.get("media_url"),
            post.get("imageUrl"),
            post.get("thumbnailUrl"),
        ]
        
        # Tenta em objetos aninhados
        if "media" in post and isinstance(post["media"], dict):
            media_paths.extend([
                post["media"].get("url"),
                post["media"].get("thumbnailUrl"),
            ])
        
        if "files" in post and isinstance(post["files"], list) and post["files"]:
            media_paths.append(post["files"][0].get("url"))
        
        for url in media_paths:
            if url:
                return str(url)
        
        return ""
    
    def extract_all(self) -> list[PostData]:
        """
        Executa extração completa: lista de posts + analytics de cada um.
        
        Returns:
            list[PostData]: Lista de posts com dados completos
        """
        results: list[PostData] = []
        
        # 1. Busca lista de posts
        posts = self.fetch_posts_list()
        
        if not posts:
            logger.warning("⚠️ Nenhum post encontrado para processar")
            return results
        
        # 2. Para cada post, busca analytics
        for i, post in enumerate(posts, 1):
            logger.info(f"📊 Processando post {i}/{len(posts)}...")
            
            # Extrai metadados básicos
            metadata = self.extract_post_metadata(post)
            
            # Busca external_id
            external_id = self.find_external_id(post)
            
            # Cria objeto PostData
            post_data = PostData(
                internal_id=metadata["internal_id"],
                external_id=external_id,
                title=metadata["title"],
                caption=metadata["caption"],
                platform=metadata["platform"],
                post_type=metadata["post_type"],
                published_at=metadata["published_at"],
                media_url=metadata["media_url"],
                permalink=metadata["permalink"],
            )
            
            # Tenta buscar analytics
            analytics = None
            analytics_error = None
            
            # Tenta primeiro com external_id (se disponível)
            if external_id:
                analytics = self.fetch_post_analytics(external_id, is_external=True)
            
            # Se não funcionou, tenta com internal_id
            if not analytics and metadata["internal_id"]:
                analytics = self.fetch_post_analytics(metadata["internal_id"], is_external=False)
            
            if analytics:
                metrics = self.extract_analytics_metrics(analytics)
                post_data.likes = metrics["likes"]
                post_data.comments = metrics["comments"]
                post_data.shares = metrics["shares"]
                post_data.saves = metrics["saves"]
                post_data.reach = metrics["reach"]
                post_data.impressions = metrics["impressions"]
                post_data.plays = metrics["plays"]
                logger.debug(f"  ✅ Analytics: {metrics['likes']} likes, {metrics['reach']} reach")
            else:
                post_data.analytics_error = "Não foi possível obter analytics"
                logger.warning(f"  ⚠️ Analytics não disponível para post {metadata['internal_id']}")
            
            results.append(post_data)
        
        logger.info(f"✅ Extração concluída: {len(results)} posts processados")
        return results
    
    def _dump_json_structure(self, data: dict, filename: str):
        """Salva JSON de debug em arquivo."""
        try:
            debug_path = Path(__file__).parent.parent / "debug"
            debug_path.mkdir(exist_ok=True)
            
            with open(debug_path / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"📝 JSON salvo em: {debug_path / filename}")
        except Exception as e:
            logger.debug(f"Não foi possível salvar debug JSON: {e}")
