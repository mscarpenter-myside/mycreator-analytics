#!/usr/bin/env python3
"""
MyCreator Analytics ETL - Multi-Workspace
==========================================

Extrai dados de performance das 4 cidades configuradas:
- Florianópolis: 696e75c20f3354d37f074866
- Florianópolis Continente: 696689afcddd41ec6a024adb  
- Goiânia: 696689f3c04f3fefdc0118cd
- MyCreator: 68fbfe91e94c0946d103643d

Fluxo:
1. Extract: Busca dados da API MyCreator (multi-workspace)
2. Transform: Converte PostData para DataFrame pandas
3. Load: Atualiza Google Sheets

Uso: python run_etl.py
"""
import sys
import time
import logging
from datetime import datetime
from dataclasses import asdict

import pandas as pd
import re

# Força output imediato no terminal (sem buffer)
sys.stdout.reconfigure(line_buffering=True)


from src.config import get_config, setup_logging
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES
from src.load import load_to_sheets


def run_etl() -> bool:
    """Executa o pipeline ETL completo."""
    
    # =========================================================================
    # SETUP
    # =========================================================================
    config = get_config()
    logger = setup_logging(debug=config.debug_mode)
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO ETL MyCreator Analytics")
    logger.info(f"📅 Data/Hora: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🎯 Workspaces: {len(TARGET_WORKSPACES)} cidades")
    for ws in TARGET_WORKSPACES:
        logger.info(f"   • {ws['name']}: {ws['id']}")
    logger.info("=" * 60)
    
    try:
        # =====================================================================
        # ETAPA 1: EXTRACT
        # =====================================================================
        logger.info("\n📡 ETAPA 1: EXTRAÇÃO")
        extractor = MyCreatorExtractor(config)
        
        # Extrai de todos os workspaces (lista fixa em TARGET_WORKSPACES)
        all_posts = extractor.extract_from_workspaces()
        
        if not all_posts:
            logger.warning("⚠️ Nenhum post extraído de nenhum workspace.")
        
        # Extrai perfis (NOVA FUNCIONALIDADE)
        logger.info("\n📡 ETAPA 1.2: EXTRAÇÃO DE PERFIS")
        all_profiles = extractor.extract_profiles()

        # Extrai Stories (NOVA FUNCIONALIDADE)
        logger.info("\n📡 ETAPA 1.3: EXTRAÇÃO DE STORIES")
        all_stories = extractor.fetch_stories_list()
        
        if not all_posts and not all_profiles and not all_stories:
            logger.warning("⚠️ Nada extraído (nem posts, nem perfis, nem stories).")
            return False
        
        # =====================================================================
        # ETAPA 2: TRANSFORM
        # =====================================================================
        logger.info("\n🔄 ETAPA 2: TRANSFORMAÇÃO")
        
        # Converte lista de dataclass para DataFrame (Posts)
        records_posts = [asdict(post) for post in all_posts]
        df_posts = pd.DataFrame(records_posts)
        
        # Converte lista de dataclass para DataFrame (Perfis)
        records_profiles = [asdict(prof) for prof in all_profiles]
        df_profiles = pd.DataFrame(records_profiles)

        # Converte lista de dataclass para DataFrame (Stories)
        records_stories = [asdict(story) for story in all_stories]
        df_stories = pd.DataFrame(records_stories)
        
        # =================================================================
        # MAPEAMENTO DE COLUNAS - ORDEM DEFINITIVA PARA DIRETORIA
        # =================================================================
        # Primeira coluna: Cidade | Última coluna: Timestamp de Atualização
        column_mapping = {
            # IDENTIFICAÇÃO (primeira: Cidade, segunda: Data de Publicação)
            "workspace_name": "Cidade",
            "published_at": "Data de Publicação",
            "platform": "Rede Social",  # Instagram, Facebook, etc
            "profile_name": "Perfil",
            "follower_count": "Seguidores",  # Total de seguidores do perfil
            "post_type": "Tipo",  # REELS, FEED, STORY
            "media_type": "Tipo de Mídia",  # Reels, Carousel, Video, Image (do Instagram Analytics)
            
            # CONTEÚDO
            "title": "Título",  # Nome do vídeo/publicação
            "caption": "Legenda",
            
            # ENGAJAMENTO
            "likes": "Likes",
            "comments": "Comentários",
            "saves": "Salvos",
            "shares": "Compartilhamentos",
            
            # PERFORMANCE
            "reach": "Alcance",
            "impressions": "Impressões",
            "plays": "Plays",
            "total_watch_time": "Tempo Assistido (seg)",
            "avg_watch_time": "Tempo Médio (seg)",
            
            # TÉCNICO (última: Timestamp de Atualização)
            "permalink": "Link",
            "external_id": "ID Instagram",
            "internal_id": "ID Interno",
            "analytics_error": "Status Dados",
            "extraction_timestamp": "Timestamp de Atualização",
        }
        
        # Seleciona e renomeia colunas existentes (preserva ordem do dict)
        columns_to_export = [col for col in column_mapping.keys() if col in df_posts.columns]
        df_final = df_posts[columns_to_export].rename(columns=column_mapping)
        
        # =================================================================
        # 4. Transforma Profiles em DataFrame (Base de Seguidores)
        records_profiles = [asdict(prof) for prof in all_profiles]
        df_profiles_raw = pd.DataFrame(records_profiles)
        
        if df_profiles_raw.empty:
            logger.warning("⚠️ Nenhum perfil extraído. Pulando aba perfis.")
            df_final_profiles = pd.DataFrame()
        else:
            # =========================================================================
            # CÁLCULO DE "MYCREATOR ANALYTICS" (Agregação Real)
            # =========================================================================
            # Em vez de usar dados gerais do Instagram, calculamos a performance DO MYCREATOR
            # com base nos posts extraídos (que são filtrados pela ferramenta).
            
            if not df_posts.empty:
                # Agrupa posts por Perfil (Nome da conta)
                # Nota: Usamos 'profile_name' como chave. Ideal seria ID, mas o nome é mais legível na planilha.
                metrics_agg = df_posts.groupby('profile_name').agg({
                    'internal_id': 'count',      # Qtd Posts MyCreator
                    'likes': 'sum',
                    'comments': 'sum',
                    'saves': 'sum',
                    'shares': 'sum',
                    'reach': 'sum',              # Alcance Acumulado MyCreator
                    'impressions': 'sum'
                }).reset_index()
                
                # Renomeia colunas para merge
                metrics_agg.rename(columns={
                    'internal_id': 'posts_mycreator',
                    'reach': 'reach_mycreator',
                    'impressions': 'impressions_mycreator'
                }, inplace=True)
                
                # Calcula Engajamento Total MyCreator
                metrics_agg['engagement_mycreator'] = (
                    metrics_agg['likes'] + 
                    metrics_agg['comments'] + 
                    metrics_agg['saves'] + 
                    metrics_agg['shares']
                )
                
                # Faz o Merge com a base de seguidores (df_profiles_raw)
                # Left join para manter perfis que existem mas não postaram nada via ferramenta ainda
                df_profiles_final = pd.merge(
                    df_profiles_raw, 
                    metrics_agg, 
                    on='profile_name', 
                    how='left'
                )
                
                # Preenche NaNs com 0 (para quem não teve posts)
                # Preenche NaNs com 0 (para quem não teve posts)
                cols_to_fill = ['posts_mycreator', 'reach_mycreator', 'impressions_mycreator', 'engagement_mycreator']
                df_profiles_final[cols_to_fill] = df_profiles_final[cols_to_fill].fillna(0)
                
                # Garante que são inteiros (remove .0)
                for col in cols_to_fill:
                    df_profiles_final[col] = df_profiles_final[col].astype(int)
                
                # Recalcula Taxa de Engajamento MyCreator (%)
                # Fórmula: (Engajamento Total / Alcance Acumulado) * 100
                # Evita divisão por zero
                df_profiles_final['engagement_rate_mycreator'] = df_profiles_final.apply(
                    lambda row: round((row['engagement_mycreator'] / row['reach_mycreator'] * 100), 2) 
                    if row['reach_mycreator'] > 0 else 0.0, 
                    axis=1
                )

                # Calcula Taxa de Alcance Média (%)
                # Fórmula: ((Alcance Acumulado / Posts) / Seguidores) * 100
                def calc_reach_rate(row):
                    if row['posts_mycreator'] == 0 or row['followers'] == 0:
                        return 0.0
                    
                    avg_reach = row['reach_mycreator'] / row['posts_mycreator']
                    return round((avg_reach / row['followers']) * 100, 2)

                df_profiles_final['reach_rate_mycreator'] = df_profiles_final.apply(calc_reach_rate, axis=1)
                
            else:
                # Se não tem posts, tudo é zero
                df_profiles_final = df_profiles_raw.copy()
                df_profiles_final['posts_mycreator'] = 0
                df_profiles_final['engagement_mycreator'] = 0
                df_profiles_final['reach_mycreator'] = 0
                df_profiles_final['engagement_rate_mycreator'] = 0.0
                df_profiles_final['reach_rate_mycreator'] = 0.0

        # 5. Seleção e Renomeação de Colunas para aba Perfis
        # Mapeamos as novas métricas calculadas em vez das genéricas
        profile_mapping = {
            "workspace_name": "Cidade",
            "profile_name": "Perfil",
            "followers": "Seguidores (Total)",
            "posts_mycreator": "Posts MyCreator",  # Nova métrica real
            "engagement_rate_mycreator": "Engajamento Médio MyCreator (%)", # Nova métrica real
            "reach_rate_mycreator": "Taxa de Alcance MyCreator (%)", # Nova métrica
            "reach_mycreator": "Alcance Acumulado MyCreator", # Nova métrica real
            "engagement_mycreator": "Interações Totais MyCreator", # Nova métrica real
            "extraction_timestamp": "Atualizado em"
        }

        columns_profiles_export = [col for col in profile_mapping.keys() if col in df_profiles_final.columns]
        df_final_profiles = df_profiles_final[columns_profiles_export].rename(columns=profile_mapping)
        
        # Formata Data de Publicação apenas como data (DD/MM/YYYY)
        if "Data de Publicação" in df_final.columns:
            df_final["Data de Publicação"] = pd.to_datetime(
                df_final["Data de Publicação"], errors='coerce'
            ).dt.strftime("%d/%m/%Y")
        
        # Ordena por cidade e data (mais recentes primeiro)
        if "Data de Publicação" in df_final.columns and "Cidade" in df_final.columns:
            df_final = df_final.sort_values(
                by=["Cidade", "Data de Publicação"], 
                ascending=[True, False]
            )
        
        # Estatísticas
        total_posts = len(df_final)
        total_likes = int(df_final["Likes"].sum()) if "Likes" in df_final.columns else 0
        total_reach = int(df_final["Alcance"].sum()) if "Alcance" in df_final.columns else 0
        total_comments = int(df_final["Comentários"].sum()) if "Comentários" in df_final.columns else 0
        
        if not df_final.empty:
            logger.info(f"📊 Total: {total_posts} posts")
            # DEBUG: Imprime tipos únicos para alinhar com Looker Studio
            if "Tipo" in df_final.columns:
                logger.info(f"   🔍 Tipos Únicos (Tipo): {df_final['Tipo'].unique()}")
            if "Tipo de Mídia" in df_final.columns:
                logger.info(f"   🔍 Mídias Únicas (Tipo de Mídia): {df_final['Tipo de Mídia'].unique()}")

        logger.info(f"❤️ Likes: {total_likes:,}")
        logger.info(f"👁️ Alcance: {total_reach:,}")
        logger.info(f"💬 Comentários: {total_comments:,}")
        
        # Resumo por cidade
        logger.info("\n📈 RESUMO POR CIDADE:")
        for cidade in df_final["Cidade"].unique():
            df_cidade = df_final[df_final["Cidade"] == cidade]
            logger.info(f"   • {cidade}: {len(df_cidade)} posts | {int(df_cidade['Likes'].sum())} likes")
        
        # =================================================================
        # 6. Processamento de Hashtags (NOVO)
        # =================================================================
        logger.info("\n🏷️ PROCESSANDO HASHTAGS...")
        
        # Função interna para extrair hashtags
        def get_hashtags(text):
            if not isinstance(text, str): return []
            return re.findall(r"#(\w+)", text)
            
        if not df_posts.empty:
            # Cria lista temporária para explosão
            df_tags_temp = df_posts[["internal_id", "caption", "likes", "comments", "saves", "shares", "reach", "impressions"]].copy()
            df_tags_temp["hashtags"] = df_tags_temp["caption"].apply(get_hashtags)
            
            # Explode para ter uma hashtag por linha
            df_hashtags_exploded = df_tags_temp.explode("hashtags")
            df_hashtags_exploded = df_hashtags_exploded[df_hashtags_exploded["hashtags"].notna()] # Remove vazios
            
            # Agregação por Hashtag
            df_hashtags_final = df_hashtags_exploded.groupby("hashtags").agg({
                "internal_id": "count",      # Qtd Usos
                "likes": "sum",
                "comments": "sum",
                "saves": "sum",
                "shares": "sum",
                "reach": "sum",
                "impressions": "sum"
            }).reset_index()
            
            # Métricas calculadas
            df_hashtags_final["engagement_total"] = (
                df_hashtags_final["likes"] + 
                df_hashtags_final["comments"] + 
                df_hashtags_final["saves"] + 
                df_hashtags_final["shares"]
            )
            
            # Renomeia colunas para PT-BR
            hashtag_mapping = {
                "hashtags": "Hashtag",
                "internal_id": "Qtd Usos",
                "engagement_total": "Engajamento Total",
                "reach": "Alcance Acumulado",
                "impressions": "Impressões Acumuladas",
                "likes": "Total Likes",
                "comments": "Total Comentários"
            }
            
            cols_export_tags = [c for c in hashtag_mapping.keys() if c in df_hashtags_final.columns]
            df_hashtags_final = df_hashtags_final[cols_export_tags].rename(columns=hashtag_mapping)
            
            # Ordena por Qtd Usos
            df_hashtags_final = df_hashtags_final.sort_values(by="Qtd Usos", ascending=False)
            
            logger.info(f"✅ {len(df_hashtags_final)} hashtags identificadas.")
        else:
            df_hashtags_final = pd.DataFrame()

        # =================================================================
        # 7. Processamento de Stories (NOVO)
        # =================================================================
        logger.info("\n📸 PROCESSANDO STORIES...")
        
        story_mapping = {
            "workspace_name": "Cidade",
            "published_at": "Data",
            "profile_name": "Perfil",
            "permalink": "Link",
            "media_url": "Preview",
            "external_id": "ID Story",
            "reach": "Alcance",
            "impressions": "Impressões",
            "exits": "Saídas",
            "replies": "Respostas",
            "taps_forward": "Avançar",
            "taps_back": "Voltar",
            "extraction_timestamp": "Atualizado em"
        }
        
        if not df_stories.empty:
            cols_export_stories = [c for c in story_mapping.keys() if c in df_stories.columns]
            df_stories_final = df_stories[cols_export_stories].rename(columns=story_mapping)
            
            # Formata Data
            if "Data" in df_stories_final.columns:
                df_stories_final["Data"] = pd.to_datetime(
                    df_stories_final["Data"], errors='coerce'
                ).dt.strftime("%d/%m/%Y %H:%M:%S")
                
            logger.info(f"✅ {len(df_stories_final)} stories processados.")
        else:
            df_stories_final = pd.DataFrame()

        # =================================================================
        # 8. Processamento de Reels (NOVO)
        # =================================================================
        logger.info("\n🎬 PROCESSANDO REELS...")
        
        # Filtra onde post_type é REEL ou media_type analytics é VIDEO/REEL
        df_reels = pd.DataFrame()
        if not df_posts.empty:
            # Normaliza para comparação
            mask_reels = (
                (df_posts['post_type'] == 'REEL') | 
                (df_posts['media_type'].astype(str).str.upper().isin(['REEL', 'REELS', 'VIDEO']))
            )
            df_reels = df_posts[mask_reels].copy()
            
        reels_mapping = {
            "workspace_name": "Cidade",
            "published_at": "Data",
            "profile_name": "Perfil",
            "permalink": "Link",
            "title": "Título",
            "video_duration": "Duração (s)",
            "total_watch_time": "Tempo Assistido (s)",
            "avg_watch_time": "Tempo Médio (s)",
            "plays": "Plays",
            "reach": "Alcance",
            "likes": "Likes",
            "comments": "Comentários",
            "shares": "Compartilhamentos",
            "saves": "Salvos",
            "engagement_rate": "Engajamento (%)",
            "extraction_timestamp": "Atualizado em"
        }
        
        if not df_reels.empty:
            cols_export_reels = [c for c in reels_mapping.keys() if c in df_reels.columns]
            df_reels_final = df_reels[cols_export_reels].rename(columns=reels_mapping)
            
            # Formata Data
            if "Data" in df_reels_final.columns:
                df_reels_final["Data"] = pd.to_datetime(
                    df_reels_final["Data"], errors='coerce'
                ).dt.strftime("%d/%m/%Y")
            
            # Ordena por Data
            if "Data" in df_reels_final.columns:
                df_reels_final = df_reels_final.sort_values(by="Data", ascending=False)
                
            logger.info(f"✅ {len(df_reels_final)} reels processados.")
        else:
            df_reels_final = pd.DataFrame()

        # =================================================================
        # 9. Processamento de Imagens (NOVO - FASE 3)
        # =================================================================
        logger.info("\n🖼️ PROCESSANDO IMAGENS...")
        
        df_images = pd.DataFrame()
        if not df_posts.empty:
            # Lógica: É FEED e NÃO é Carrossel nem Vídeo
            # Identifica carrossel e vídeo para excluir
            mask_carousel_video = (
                (df_posts['post_type'] == 'CAROUSEL_ALBUM') | 
                (df_posts['media_type'].astype(str).str.upper().isin(['CAROUSEL', 'CAROUSEL_ALBUM', 'REEL', 'REELS', 'VIDEO']))
            )
            
            mask_images = (
                (df_posts['post_type'] == 'FEED') & 
                (~mask_carousel_video)
            )
            
            df_images = df_posts[mask_images].copy()
            
        common_mapping = {
            "workspace_name": "Cidade",
            "published_at": "Data",
            "profile_name": "Perfil",
            "permalink": "Link",
            "title": "Legenda/Título",
            "likes": "Likes",
            "comments": "Comentários",
            "shares": "Compartilhamentos",
            "saves": "Salvos",
            "reach": "Alcance",
            "impressions": "Impressões",
            "engagement_rate": "Engajamento (%)",
            "extraction_timestamp": "Atualizado em"
        }
        
        if not df_images.empty:
            cols_img = [c for c in common_mapping.keys() if c in df_images.columns]
            df_images_final = df_images[cols_img].rename(columns=common_mapping)
             # Formata Data
            if "Data" in df_images_final.columns:
                df_images_final["Data"] = pd.to_datetime(df_images_final["Data"], errors='coerce').dt.strftime("%d/%m/%Y")
            df_images_final = df_images_final.sort_values(by="Data", ascending=False)
            logger.info(f"✅ {len(df_images_final)} imagens processadas.")
        else:
            df_images_final = pd.DataFrame()

        # =================================================================
        # 10. Processamento de Carrossel (NOVO - FASE 3)
        # =================================================================
        logger.info("\n🎠 PROCESSANDO CARROSSEIS...")
        
        df_carousels = pd.DataFrame()
        if not df_posts.empty:
            mask_carousels = (
                (df_posts['post_type'] == 'CAROUSEL_ALBUM') | 
                (df_posts['media_type'].astype(str).str.upper().isin(['CAROUSEL', 'CAROUSEL_ALBUM']))
            )
            df_carousels = df_posts[mask_carousels].copy()
            
        if not df_carousels.empty:
            cols_car = [c for c in common_mapping.keys() if c in df_carousels.columns]
            df_carousels_final = df_carousels[cols_car].rename(columns=common_mapping)
             # Formata Data
            if "Data" in df_carousels_final.columns:
                df_carousels_final["Data"] = pd.to_datetime(df_carousels_final["Data"], errors='coerce').dt.strftime("%d/%m/%Y")
            df_carousels_final = df_carousels_final.sort_values(by="Data", ascending=False)
            logger.info(f"✅ {len(df_carousels_final)} carrosseis processados.")
        else:
            df_carousels_final = pd.DataFrame()

        # =================================================================
        # 10.1. Processamento UNIFICADO (Base Looker Studio) (NOVO)
        # =================================================================
        logger.info("\n📊 PROCESSANDO BASE UNIFICADA (LOOKER)...")
        
        df_unified = pd.DataFrame()
        if not df_posts.empty:
            # 1. Usa TODOS os posts para garantir a mesma contagem de "Dados Brutos"
            # (Removemos o filtro restritivo anterior)
            df_uni_raw = df_posts.copy()
            
            # Função para padronizar tipo de mídia (Reels, Imagem, Carrousel)
            def standardize_media_type(row):
                p_type = str(row.get('post_type', '')).upper()
                m_type = str(row.get('media_type', '')).upper()
                
                # Reels / Vídeo
                if p_type in ['REEL', 'REELS', 'VIDEO', 'IGTV'] or m_type in ['REEL', 'REELS', 'VIDEO', 'IGTV']:
                    return 'Reels'
                # Carrossel (Usuario solicitou com 2 'r')
                elif p_type in ['CAROUSEL_ALBUM', 'CAROUSEL', 'SIDE_CAR'] or m_type in ['CAROUSEL', 'CAROUSEL_ALBUM', 'SIDE_CAR']:
                    return 'Carrousel'
                # Imagem / Feed
                elif p_type in ['IMAGE', 'FEED'] or m_type in ['IMAGE', 'FEED']:
                    return 'Imagem'
                else:
                    return 'Outros' # Para identificar posts perdidos

            df_uni_raw['media_type_std'] = df_uni_raw.apply(standardize_media_type, axis=1)
            
            # Garante colunas de vídeo (preenche com 0 se não existir ou se não for vídeo)
            video_cols = ['video_duration', 'total_watch_time', 'avg_watch_time', 'plays']
            for vc in video_cols:
                if vc not in df_uni_raw.columns:
                    df_uni_raw[vc] = 0
                else:
                    df_uni_raw[vc] = df_uni_raw[vc].fillna(0)
            
            # Garante coluna plays (se vazio, usa impressões como proxy para Reels, ou vice-versa)
            if 'plays' in df_uni_raw.columns:
                 df_uni_raw['impressions'] = df_uni_raw[['impressions', 'plays']].max(axis=1)

            # Calcula Taxa de Alcance Individual (%)
            # Fórmula: (Alcance / Seguidores) * 100
            def calc_post_reach_rate(row):
                followers = row.get('follower_count', 0)
                reach = row.get('reach', 0)
                if followers > 0:
                    return round((reach / followers) * 100, 2)
                return 0.0

            df_uni_raw['reach_rate'] = df_uni_raw.apply(calc_post_reach_rate, axis=1)

            # Selecão e Renomeação
            unified_mapping = {
                "internal_id": "ID Post",
                "published_at": "Data",
                "workspace_name": "Cidade",
                "profile_name": "Perfil",
                "platform": "Rede Social",
                "follower_count": "Seguidores",
                "media_type_std": "Tipo de Mídia",
                "permalink": "Link",
                "title": "Legenda/Título",
                "reach": "Alcance",
                "reach_rate": "Taxa de Alcance (%)",
                "impressions": "Impressões",
                "engagement_rate": "Engajamento (%)",
                "likes": "Likes",
                "comments": "Comentários",
                "saves": "Salvos",
                "shares": "Compartilhamentos",
                "extraction_timestamp": "Atualizado em"
            }
            
            cols_uni = [c for c in unified_mapping.keys() if c in df_uni_raw.columns]
            df_unified = df_uni_raw[cols_uni].rename(columns=unified_mapping)
            
             # Formata Data e Ordena
            if "Data" in df_unified.columns:
                df_unified["Data"] = pd.to_datetime(df_unified["Data"], errors='coerce').dt.strftime("%d/%m/%Y")
            
            df_unified = df_unified.sort_values(by="Data", ascending=False)
            logger.info(f"✅ {len(df_unified)} linhas na Base Unificada.")

        # =================================================================
        # 11. Processamento de Destaques (Top Posts) (NOVO - FASE 3)
        # =================================================================
        logger.info("\n🏆 PROCESSANDO DESTAQUES...")
        
        # =================================================================
        # 11. Processamento de Destaques (MONITORAMENTO) (ATUALIZADO)
        # =================================================================
        logger.info("\n🏆 PROCESSANDO MONITORAMENTO (DESTAQUES)...")
        
        df_highlights = pd.DataFrame()
        
        if not df_posts.empty:
            # Garante que a coluna platform existe
            if 'platform' not in df_posts.columns:
                df_posts['platform'] = 'Instagram'
            
            # Agrupamento por Cidade e Plataforma
            # Métricas: Contagem, Média de Engajamento, Soma de Alcance/Impressões
            df_highlights = df_posts.groupby(['workspace_name', 'platform']).agg({
                'internal_id': 'count',
                'engagement_rate': 'mean',
                'reach': 'sum',
                'impressions': 'sum'
            }).reset_index()
            
            # Renomeia colunas para o padrão solicitado
            df_highlights = df_highlights.rename(columns={
                'workspace_name': 'Cidade',
                'platform': 'Rede Social',
                'internal_id': 'Contagem de Posts',
                'engagement_rate': 'Engajamento Médio (%)',
                'reach': 'Alcance Total',
                'impressions': 'Impressões Totais'
            })
            
            # Formatação
            df_highlights['Engajamento Médio (%)'] = df_highlights['Engajamento Médio (%)'].round(2)
            
            # Adiciona Timestamp
            df_highlights['Atualizado em'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            logger.info(f"✅ {len(df_highlights)} linhas de monitoramento geradas.")
        else:
            logger.warning("⚠️ Nenhum dado para monitoramento.")

        # =========================================================================
        # 10. HISTÓRICO DIÁRIO MYCREATOR (Publishing Behavior e Insights)
        # =========================================================================
        # Agrupa posts por Data e Perfil para criar histórico
        # Métricas: Qtd Posts, Alcance, Impressões, Engajamento
        if not df_posts.empty:
            # Garante que as colunas numéricas estão certas
            cols_to_sum = ['reach', 'impressions', 'likes', 'comments', 'shares', 'saves']
            for col in cols_to_sum:
                if col in df_posts.columns:
                    df_posts[col] = pd.to_numeric(df_posts[col], errors='coerce').fillna(0)
            
            # Cria coluna de Engajamento Total (soma das interações) se não existir
            if 'engagement_total' not in df_posts.columns:
                df_posts['engagement_total'] = (
                    df_posts['likes'] + 
                    df_posts['comments'] + 
                    df_posts['shares'] + 
                    df_posts['saves']
                )

            # Agrupa
            df_history = df_posts.groupby(['published_at', 'workspace_name', 'profile_name', 'platform']).agg({
                'internal_id': 'count',
                'reach': 'sum',
                'impressions': 'sum',
                'engagement_total': 'sum',
                'plays': 'sum',
                'total_watch_time': 'sum'
            }).reset_index()

            # Renomeia
            df_history = df_history.rename(columns={
                'published_at': 'Data',
                'workspace_name': 'Cidade',
                'profile_name': 'Perfil',
                'platform': 'Rede',
                'internal_id': 'Posts Publicados',
                'reach': 'Alcance (Soma)',
                'impressions': 'Impressões (Soma)',
                'engagement_total': 'Engajamento (Soma)',
                'plays': 'Plays (Soma)',
                'total_watch_time': 'Tempo Assistido Total (Seg)'
            })
            
            # Ordena por data decrescente
            df_history = df_history.sort_values(by='Data', ascending=False)
            logger.info(f"✅ {len(df_history)} linhas de Histórico Diário geradas.")
        else:
            df_history = pd.DataFrame()

        # =========================================================================
        # 11. TOP POSTS MYCREATOR (Rankings)
        # =========================================================================
        if not df_posts.empty:
            # Vamos pegar o Top 20 de cada métrica
            top_reach = df_posts.nlargest(20, 'reach')[['permalink', 'reach', 'title', 'profile_name', 'published_at', 'media_type']].copy()
            top_reach['Rank_Tipo'] = 'Alcance'
            top_reach = top_reach.rename(columns={'reach': 'Valor_Metrica'})

            top_engage = df_posts.nlargest(20, 'engagement_total')[['permalink', 'engagement_total', 'title', 'profile_name', 'published_at', 'media_type']].copy()
            top_engage['Rank_Tipo'] = 'Engajamento'
            top_engage = top_engage.rename(columns={'engagement_total': 'Valor_Metrica'})

            top_impressions = df_posts.nlargest(20, 'impressions')[['permalink', 'impressions', 'title', 'profile_name', 'published_at', 'media_type']].copy()
            top_impressions['Rank_Tipo'] = 'Impressões'
            top_impressions = top_impressions.rename(columns={'impressions': 'Valor_Metrica'})

            # Concatena
            df_top_posts = pd.concat([top_reach, top_engage, top_impressions])
            
            # Formata
            df_top_posts['Valor_Metrica'] = df_top_posts['Valor_Metrica'].astype(int)
            df_top_posts = df_top_posts[['Rank_Tipo', 'Valor_Metrica', 'profile_name', 'published_at', 'media_type', 'title', 'permalink']]
            df_top_posts = df_top_posts.rename(columns={
                'profile_name': 'Perfil',
                'published_at': 'Data',
                'media_type': 'Tipo',
                'title': 'Legenda/Titulo',
                'permalink': 'Link'
            })
            logger.info(f"✅ {len(df_top_posts)} Top Posts gerados.")
        else:
            df_top_posts = pd.DataFrame()

        # =========================================================================
        # 12. SNAPSHOT SEGUIDORES (Diário)
        # =========================================================================
        # Prepara dados para o append diário
        if not df_profiles.empty:
            df_snapshot = df_profiles[['workspace_name', 'profile_name', 'followers', 'extraction_timestamp']].copy()
            # Adiciona data do snapshot (apenas data YYYY-MM-DD para o BigQuery futuramente)
            df_snapshot['Data_Snapshot'] = datetime.now().strftime("%Y-%m-%d")
            
            # Reordena: Data, Workspace, Perfil, Seguidores
            df_snapshot = df_snapshot[['Data_Snapshot', 'workspace_name', 'profile_name', 'followers']]
            df_snapshot = df_snapshot.rename(columns={
                'workspace_name': 'Cidade',
                'profile_name': 'Perfil',
                'followers': 'Seguidores'
            })
            logger.info(f"✅ {len(df_snapshot)} linhas de Snapshot de Seguidores preparadas.")
        else:
            df_snapshot = pd.DataFrame()

        # =====================================================================
        # ETAPA 3: LOAD (GOOGLE SHEETS)
        # =====================================================================
        logger.info("\n📤 ETAPA 3: CARGA NO GOOGLE SHEETS")
        logger.info(f"📑 Sheet ID: {config.google_sheet_id}")
        logger.info(f"📑 Aba Posts: {config.sheet_tab_name}")
        logger.info(f"📑 Aba Perfis: Perfis")
        logger.info(f"📑 Aba Stories: Stories_Detalhado")

        logger.info(f"📑 Aba Hashtags: Hashtags_Analitico")
        logger.info(f"📑 Aba Reels: Reels_Detalhado")
        logger.info(f"📑 Aba Imagens: Imagens_Detalhado")
        logger.info(f"📑 Aba Carro: Carrossel_Detalhado")
        logger.info(f"📑 Aba Monitoramento: Redes_Monitoramento")
        logger.info(f"📑 Aba Histórico: Historico_Diario_MyCreator")
        logger.info(f"📑 Aba Top Posts: Top_Posts_MyCreator")
        logger.info(f"📑 Aba Snapshot: Snapshot_Seguidores (APPEND)")
        logger.info(f"📝 Modo: {config.write_mode}")
        
        # Carga 1: Posts (Aba padrão)
        success_posts = True
        if not df_final.empty:
            logger.info(f"Uploading Posts ({len(df_final)} linhas)...")
            success_posts = load_to_sheets(df_final, config, tab_name=config.sheet_tab_name)
            time.sleep(10) # Avoid Rate Limit
        
        # Carga 2: Perfis (Nova aba)
        success_profiles = True
        if not df_final_profiles.empty:
            logger.info(f"Uploading Perfis ({len(df_final_profiles)} linhas)...")
            success_profiles = load_to_sheets(df_final_profiles, config, tab_name="Perfis")
            time.sleep(10)


        # Carga 6: Imagens (Aba Imagens_Detalhado)
        success_images = True
        if not df_images_final.empty:
            logger.info(f"Uploading Imagens_Detalhado ({len(df_images_final)} linhas)...")
            success_images = load_to_sheets(df_images_final, config, tab_name="Imagens_Detalhado")
            time.sleep(10)

        # Carga 7: Carrossel (Aba Carrossel_Detalhado)
        success_carousels = True
        if not df_carousels_final.empty:
            logger.info(f"Uploading Carrossel_Detalhado ({len(df_carousels_final)} linhas)...")
            success_carousels = load_to_sheets(df_carousels_final, config, tab_name="Carrossel_Detalhado")
            time.sleep(10)

        # Carga 8: Monitoramento (Aba Redes_Monitoramento)
        success_highlights = True
        if not df_highlights.empty:
            logger.info(f"Uploading Redes_Monitoramento ({len(df_highlights)} linhas)...")
            success_highlights = load_to_sheets(df_highlights, config, tab_name="Redes_Monitoramento")
            time.sleep(10)
            
        # Carga 3: Hashtags (Nova aba)
        success_hashtags = True
        if not df_hashtags_final.empty:
            logger.info(f"Uploading Hashtags_Analitico ({len(df_hashtags_final)} linhas)...")
            success_hashtags = load_to_sheets(df_hashtags_final, config, tab_name="Hashtags_Analitico")
            time.sleep(10)

        # Carga 4: Stories (Nova aba)
        success_stories = True
        if not df_stories_final.empty:
            logger.info(f"Uploading Stories_Detalhado ({len(df_stories_final)} linhas)...")
            success_stories = load_to_sheets(df_stories_final, config, tab_name="Stories_Detalhado")
            time.sleep(10)

        # Carga 5: Reels (Nova aba)
        success_reels = True
        if not df_reels_final.empty:
            logger.info(f"Uploading Reels_Detalhado ({len(df_reels_final)} linhas)...")
            success_reels = load_to_sheets(df_reels_final, config, tab_name="Reels_Detalhado")
            time.sleep(10)

        # Carga 9: Base Unificada (Aba Base_Looker_Unificada)
        success_unified = True
        if not df_unified.empty:
            logger.info(f"Uploading Base_Looker_Unificada ({len(df_unified)} linhas)...")
            success_unified = load_to_sheets(df_unified, config, tab_name="Base_Looker_Unificada")
            time.sleep(10)
            
        # Carga 10: Histórico Diário
        success_history = True
        if not df_history.empty:
            logger.info(f"Uploading Historico_Diario_MyCreator ({len(df_history)} linhas)...")
            success_history = load_to_sheets(df_history, config, tab_name="Historico_Diario_MyCreator")
            time.sleep(10)

        # Carga 11: Top Posts
        success_top = True
        if not df_top_posts.empty:
            logger.info(f"Uploading Top_Posts_MyCreator ({len(df_top_posts)} linhas)...")
            success_top = load_to_sheets(df_top_posts, config, tab_name="Top_Posts_MyCreator")
            time.sleep(10)
            
        # Carga 12: Snapshot Seguidores (APPEND FORÇADO)
        success_snapshot = True
        if not df_snapshot.empty:
            logger.info(f"Uploading Snapshot_Seguidores ({len(df_snapshot)} linhas) [APPEND]...")
            # Cria config temporária para forçar append
            from dataclasses import replace
            config_append = replace(config, write_mode="append")
            success_snapshot = load_to_sheets(df_snapshot, config_append, tab_name="Snapshot_Seguidores")
            time.sleep(5)
        
        if not success_posts or not success_profiles or not success_hashtags or not success_stories or not success_reels or not success_images or not success_carousels or not success_highlights or not success_unified or not success_history or not success_top or not success_snapshot:
            logger.error("❌ Falha parcial na atualização do Google Sheets!")
        
        if all([success_posts, success_profiles, success_hashtags, success_stories, success_reels, success_images, success_carousels, success_highlights, success_unified, success_history, success_top, success_snapshot]):
            logger.info("✅ Google Sheets (Todas as 12 abas) atualizado com sucesso!")
        
        # =====================================================================
        # RESUMO FINAL
        # =====================================================================
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("🏁 ETL CONCLUÍDO COM SUCESSO!")
        logger.info(f"⏱️ Duração: {duration:.2f} segundos")
        logger.info(f"⏱️ Duração: {duration:.2f} segundos")
        logger.info(f"📊 Posts processados: {total_posts}")
        logger.info(f"👥 Perfis processados: {len(df_final_profiles)}")
        logger.info(f"📄 Sheets: https://docs.google.com/spreadsheets/d/{config.google_sheet_id}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erro fatal: {e}")
        return False


if __name__ == "__main__":
    success = run_etl()
    sys.exit(0 if success else 1)
