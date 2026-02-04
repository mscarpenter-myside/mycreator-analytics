"""
Módulo de Transformação (Transform) do ETL.

Responsável por limpar, calcular métricas derivadas e formatar
os dados extraídos para carregamento no Google Sheets.
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from .extract import PostData

logger = logging.getLogger("mycreator_etl")


class DataTransformer:
    """
    Transformador de dados do ETL.
    
    Converte PostData em DataFrame pandas com métricas calculadas
    e formatação adequada para Google Sheets.
    """
    
    def __init__(self):
        """Inicializa o transformador."""
        self.processed_count = 0
        self.error_count = 0
    
    def transform(self, posts: list[PostData]) -> pd.DataFrame:
        """
        Transforma lista de PostData em DataFrame.
        
        Args:
            posts: Lista de dados extraídos
            
        Returns:
            pd.DataFrame: Dados transformados
        """
        if not posts:
            logger.warning("⚠️ Nenhum dado para transformar")
            return pd.DataFrame()
        
        logger.info(f"🔄 Transformando {len(posts)} posts...")
        
        # Converte para lista de dicts
        records = []
        for post in posts:
            record = self._post_to_record(post)
            if record:
                records.append(record)
                self.processed_count += 1
            else:
                self.error_count += 1
        
        # Cria DataFrame
        df = pd.DataFrame(records)
        
        # Ordena colunas
        df = self._reorder_columns(df)
        
        # Formata datas
        df = self._format_dates(df)
        
        logger.info(f"✅ Transformação concluída: {self.processed_count} sucessos, {self.error_count} erros")
        
        return df
    
    def _post_to_record(self, post: PostData) -> Optional[dict]:
        """
        Converte PostData em dicionário para DataFrame.
        
        Args:
            post: Dados do post
            
        Returns:
            dict: Registro formatado
        """
        try:
            # Calcula taxa de engajamento
            engagement_rate = self._calculate_engagement_rate(
                likes=post.likes,
                saves=post.saves,
                comments=post.comments,
                reach=post.reach,
            )
            
            # Calcula total de interações
            total_interactions = post.likes + post.saves + post.comments + post.shares
            
            return {
                # Identificadores
                "ID Interno": post.internal_id,
                "ID Externo": post.external_id or "N/A",
                
                # Metadados
                "Título": self._clean_text(post.title),
                "Legenda": self._truncate_text(post.caption, max_length=500),
                "Plataforma": post.platform or "N/A",
                "Tipo": post.post_type or "N/A",
                "Data Publicação": post.published_at,
                "Link": post.permalink or "N/A",
                
                # Métricas brutas
                "Likes": post.likes,
                "Comentários": post.comments,
                "Compartilhamentos": post.shares,
                "Salvos": post.saves,
                "Alcance": post.reach,
                "Impressões": post.impressions,
                "Plays": post.plays,
                
                # Métricas calculadas
                "Total Interações": total_interactions,
                "Taxa Engajamento (%)": engagement_rate,
                
                # Status
                "Erro Analytics": post.analytics_error or "",
                
                # Metadados de extração
                "Extraído Em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.error(f"❌ Erro ao converter post {post.internal_id}: {e}")
            return None
    
    def _calculate_engagement_rate(
        self,
        likes: int,
        saves: int,
        comments: int,
        reach: int,
    ) -> float:
        """
        Calcula taxa de engajamento.
        
        Fórmula: (Likes + Saves + Comments) / Reach * 100
        
        Args:
            likes: Número de curtidas
            saves: Número de salvamentos
            comments: Número de comentários
            reach: Alcance do post
            
        Returns:
            float: Taxa de engajamento em porcentagem (0-100)
        """
        if reach <= 0:
            return 0.0
        
        total_engagement = likes + saves + comments
        rate = (total_engagement / reach) * 100
        
        # Arredonda para 2 casas decimais
        return round(rate, 2)
    
    def _clean_text(self, text: Optional[str]) -> str:
        """
        Limpa texto removendo caracteres problemáticos.
        
        Args:
            text: Texto a limpar
            
        Returns:
            str: Texto limpo
        """
        if not text:
            return ""
        
        # Remove caracteres de controle
        cleaned = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
        
        # Remove espaços extras
        cleaned = " ".join(cleaned.split())
        
        return cleaned.strip()
    
    def _truncate_text(self, text: Optional[str], max_length: int = 500) -> str:
        """
        Trunca texto se exceder tamanho máximo.
        
        Args:
            text: Texto a truncar
            max_length: Tamanho máximo
            
        Returns:
            str: Texto truncado
        """
        cleaned = self._clean_text(text)
        
        if len(cleaned) <= max_length:
            return cleaned
        
        return cleaned[:max_length - 3] + "..."
    
    def _format_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Formata colunas de data para YYYY-MM-DD.
        
        Args:
            df: DataFrame com dados
            
        Returns:
            pd.DataFrame: DataFrame com datas formatadas
        """
        date_columns = ["Data Publicação"]
        
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].apply(self._parse_date)
        
        return df
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """
        Parseia string de data para formato YYYY-MM-DD.
        
        Args:
            date_str: String de data em formato variável
            
        Returns:
            str: Data formatada ou string original se falhar
        """
        if not date_str:
            return ""
        
        # Formatos comuns de data
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 com microsegundos
            "%Y-%m-%dT%H:%M:%SZ",      # ISO 8601
            "%Y-%m-%dT%H:%M:%S",       # ISO sem timezone
            "%Y-%m-%d %H:%M:%S",       # Datetime padrão
            "%Y-%m-%d",                # Data simples
            "%d/%m/%Y %H:%M:%S",       # BR datetime
            "%d/%m/%Y",                # BR date
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # Tenta extrair só a parte da data se vier com timezone
        try:
            # Remove timezone info
            date_part = str(date_str).split("T")[0].split(" ")[0]
            if len(date_part) == 10 and date_part.count("-") == 2:
                return date_part
        except Exception:
            pass
        
        logger.debug(f"Não foi possível parsear data: {date_str}")
        return str(date_str)
    
    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reordena colunas do DataFrame para melhor visualização.
        
        Args:
            df: DataFrame original
            
        Returns:
            pd.DataFrame: DataFrame com colunas reordenadas
        """
        preferred_order = [
            "Data Publicação",
            "Plataforma",
            "Tipo",
            "Título",
            "Legenda",
            "Likes",
            "Comentários",
            "Salvos",
            "Compartilhamentos",
            "Total Interações",
            "Alcance",
            "Impressões",
            "Plays",
            "Taxa Engajamento (%)",
            "Link",
            "ID Externo",
            "ID Interno",
            "Erro Analytics",
            "Extraído Em",
        ]
        
        # Filtra só colunas que existem
        existing_columns = [col for col in preferred_order if col in df.columns]
        
        # Adiciona colunas não listadas no final
        other_columns = [col for col in df.columns if col not in preferred_order]
        
        return df[existing_columns + other_columns]
    
    def get_summary(self, df: pd.DataFrame) -> dict:
        """
        Gera resumo estatístico dos dados transformados.
        
        Args:
            df: DataFrame transformado
            
        Returns:
            dict: Resumo estatístico
        """
        if df.empty:
            return {"total_posts": 0}
        
        summary = {
            "total_posts": len(df),
            "posts_com_analytics": len(df[df["Erro Analytics"] == ""]),
            "posts_sem_analytics": len(df[df["Erro Analytics"] != ""]),
            "total_likes": df["Likes"].sum(),
            "total_comentarios": df["Comentários"].sum(),
            "alcance_total": df["Alcance"].sum(),
            "media_engajamento": round(df["Taxa Engajamento (%)"].mean(), 2),
            "melhor_engajamento": round(df["Taxa Engajamento (%)"].max(), 2),
        }
        
        # Plataformas únicas
        if "Plataforma" in df.columns:
            summary["plataformas"] = df["Plataforma"].unique().tolist()
        
        return summary
