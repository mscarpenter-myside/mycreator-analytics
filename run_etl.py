#!/usr/bin/env python3
"""
MyCreator Analytics ETL - Multi-Workspace
==========================================

Extrai dados de performance das cidades configuradas:

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
import requests

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
        
        # Extrai Crescimento de Seguidores (audience_growth)
        logger.info("\n📡 ETAPA 1.4: EXTRAÇÃO DE CRESCIMENTO DE SEGUIDORES")
        audience_growth_data = extractor.extract_audience_growth()
        
        if not all_posts and not audience_growth_data:
            logger.warning("⚠️ Nada extraído (nem posts, nem crescimento de seguidores).")
            return False
        
        # =====================================================================
        # ETAPA 2: TRANSFORM
        # =====================================================================
        logger.info("\n🔄 ETAPA 2: TRANSFORMAÇÃO")
        
        # Converte lista de dataclass para DataFrame (Posts)
        records_posts = [asdict(post) for post in all_posts]
        df_posts = pd.DataFrame(records_posts)
        
        # =================================================================
        # LIMPEZA ESPECIAL DE DADOS: REMOVER AGENDAMENTOS FALHOS
        # Remove os posts que a API retorna como 'published', 
        # mas não possuem link ou id externo (falharam na prática).
        # =================================================================
        if not df_posts.empty:
            posts_iniciais = len(df_posts)
            # Filtro: Mantém apenas posts com permalink (link) válido e external_id
            df_posts = df_posts[df_posts['permalink'].astype(str).str.strip().astype(bool) & df_posts['external_id'].notna()].copy()
            posts_removidos = posts_iniciais - len(df_posts)
            if posts_removidos > 0:
                logger.warning(f"Removidos {posts_removidos} posts com link quebrado/falha (falso 'published') da base.")
        

        # Converte lista de dicts para DataFrame (Crescimento Seguidores)
        df_audience_growth = pd.DataFrame(audience_growth_data) if audience_growth_data else pd.DataFrame()
        
        # Limpeza do audience_growth (Transform)
        if not df_audience_growth.empty:
            # 1. Remove dias sem dados (seguidores = 0)
            df_audience_growth = df_audience_growth[df_audience_growth["seguidores"] > 0].copy()
            
            # 2. Neutraliza spike inicial: para cada perfil, a primeira linha
            #    tem variacao_diaria = total de seguidores (não é variação real)
            for perfil in df_audience_growth["perfil"].unique():
                mask = df_audience_growth["perfil"] == perfil
                first_idx = df_audience_growth.loc[mask].index[0]
                df_audience_growth.loc[first_idx, "variacao_diaria"] = 0
            
            logger.info(f"📊 Crescimento: {len(df_audience_growth)} registros válidos após limpeza")
        
        # =================================================================
        # MAPEAMENTO DE COLUNAS - snake_case
        # =================================================================
        column_mapping = {
            # IDENTIFICAÇÃO
            "workspace_name": "cidade",
            "published_at": "data_publicacao",
            "platform": "rede_social",
            "profile_name": "perfil",
            "follower_count": "seguidores",
            "post_type": "formato",
            "media_type": "tipo_midia",
            
            # CONTEÚDO
            "title": "titulo",
            "caption": "legenda",
            
            # ENGAJAMENTO
            "likes": "curtidas",
            "comments": "comentarios",
            "saves": "salvos",
            "shares": "compartilhamentos",
            
            # PERFORMANCE
            "reach": "alcance",
            "reach_rate": "taxa_alcance",
            
            # TÉCNICO
            "permalink": "link",
            "external_id": "id_instagram",
            "internal_id": "id_interno",
            "analytics_error": "status_dados",
            "extraction_timestamp": "timestamp",
        }
        
        # Seleciona e renomeia colunas existentes (preserva ordem do dict)
        # Calcula Reach Rate antes de exportar
        if not df_posts.empty and "reach" in df_posts.columns and "follower_count" in df_posts.columns:
            df_posts["reach_rate"] = df_posts.apply(
                lambda x: round((x["reach"] / x["follower_count"]), 4) if x["follower_count"] > 0 else 0, 
                axis=1
            )
        
        columns_to_export = [col for col in column_mapping.keys() if col in df_posts.columns]
        df_final = df_posts[columns_to_export].rename(columns=column_mapping)
        
        
        # Formata Data de Publicação apenas como data (DD/MM/YYYY)
        if "data_publicacao" in df_final.columns:
            df_final["data_publicacao"] = pd.to_datetime(
                df_final["data_publicacao"], errors='coerce'
            ).dt.strftime("%d/%m/%Y")
        
        # Ordena por cidade e data (mais recentes primeiro)
        if "data_publicacao" in df_final.columns and "cidade" in df_final.columns:
            df_final = df_final.sort_values(
                by=["cidade", "data_publicacao"], 
                ascending=[True, False]
            )
        
        # Estatísticas
        total_posts = len(df_final)
        total_likes = int(df_final["curtidas"].sum()) if "curtidas" in df_final.columns else 0
        total_reach = int(df_final["alcance"].sum()) if "alcance" in df_final.columns else 0
        total_comments = int(df_final["comentarios"].sum()) if "comentarios" in df_final.columns else 0
        
        if not df_final.empty:
            logger.info(f"📊 Total: {total_posts} posts")
            # DEBUG: Imprime tipos únicos para alinhar com Looker Studio
            if "formato" in df_final.columns:
                logger.info(f"   🔍 Tipos Únicos (formato): {df_final['formato'].unique()}")
            if "tipo_midia" in df_final.columns:
                logger.info(f"   🔍 Mídias Únicas (tipo_midia): {df_final['tipo_midia'].unique()}")

        logger.info(f"❤️ Likes: {total_likes:,}")
        logger.info(f"👁️ Alcance: {total_reach:,}")
        logger.info(f"💬 Comentários: {total_comments:,}")
        
        # Resumo por cidade
        logger.info("\n📈 RESUMO POR CIDADE:")
        for cidade in df_final["cidade"].unique():
            df_cidade = df_final[df_final["cidade"] == cidade]
            logger.info(f"   • {cidade}: {len(df_cidade)} posts | {int(df_cidade['curtidas'].sum())} curtidas")
        
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
                "hashtags": "hashtag",
                "internal_id": "qtd_usos",
                "engagement_total": "engajamento_total",
                "reach": "alcance_acumulado",
                "impressions": "impressoes_acumuladas",
                "likes": "total_likes",
                "comments": "total_comentarios"
            }
            
            cols_export_tags = [c for c in hashtag_mapping.keys() if c in df_hashtags_final.columns]
            df_hashtags_final = df_hashtags_final[cols_export_tags].rename(columns=hashtag_mapping)
            
            # Ordena por qtd_usos
            df_hashtags_final = df_hashtags_final.sort_values(by="qtd_usos", ascending=False)
            
            logger.info(f"✅ {len(df_hashtags_final)} hashtags identificadas.")
        else:
            df_hashtags_final = pd.DataFrame()


        # =================================================================
        # 7. Processamento de Destaques (Top Posts) (NOVO - FASE 3)
        # =================================================================
        logger.info("\n🏆 PROCESSANDO DESTAQUES...")
        
        # =================================================================
        # 8. Processamento de Destaques (MONITORAMENTO) (ATUALIZADO)
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
            
            # Renomeia colunas para o padrão snake_case
            df_highlights = df_highlights.rename(columns={
                'workspace_name': 'cidade',
                'platform': 'rede_social',
                'internal_id': 'contagem_posts',
                'engagement_rate': 'engajamento_medio',
                'reach': 'alcance_total',
                'impressions': 'impressoes_totais'
            })
            
            # Formatação
            df_highlights['engajamento_medio'] = df_highlights['engajamento_medio'].round(2)
            
            # Adiciona Timestamp
            df_highlights['timestamp'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            logger.info(f"✅ {len(df_highlights)} linhas de monitoramento geradas.")
        else:
            logger.warning("⚠️ Nenhum dado para monitoramento.")


        # =========================================================================
        # 10. TOP POSTS MYCREATOR (Rankings)
        # =========================================================================
        if not df_posts.empty:
            # Garantir a criação da coluna engagement_total para rankeamento
            interaction_cols = ['likes', 'comments', 'shares', 'saves']
            actual_cols = [c for c in interaction_cols if c in df_posts.columns]
            df_posts['engagement_total'] = df_posts[actual_cols].fillna(0).sum(axis=1) if actual_cols else 0
            
            # Vamos pegar o Top 20 de cada métrica
            top_reach = df_posts.nlargest(20, 'reach')[['permalink', 'reach', 'title', 'profile_name', 'published_at', 'media_type']].copy()
            top_reach['Rank_Tipo'] = 'alcance'
            top_reach = top_reach.rename(columns={'reach': 'Valor_Metrica'})

            top_engage = df_posts.nlargest(20, 'engagement_total')[['permalink', 'engagement_total', 'title', 'profile_name', 'published_at', 'media_type']].copy()
            top_engage['Rank_Tipo'] = 'engajamento'
            top_engage = top_engage.rename(columns={'engagement_total': 'Valor_Metrica'})

            top_impressions = df_posts.nlargest(20, 'impressions')[['permalink', 'impressions', 'title', 'profile_name', 'published_at', 'media_type']].copy()
            top_impressions['Rank_Tipo'] = 'impressoes'
            top_impressions = top_impressions.rename(columns={'impressions': 'Valor_Metrica'})

            # Concatena
            df_top_posts = pd.concat([top_reach, top_engage, top_impressions])
            
            # Formata
            df_top_posts['Valor_Metrica'] = df_top_posts['Valor_Metrica'].astype(int)
            df_top_posts = df_top_posts[['Rank_Tipo', 'Valor_Metrica', 'profile_name', 'published_at', 'media_type', 'title', 'permalink']]
            df_top_posts = df_top_posts.rename(columns={
                'Rank_Tipo': 'rank_tipo',
                'Valor_Metrica': 'valor_metrica',
                'profile_name': 'perfil',
                'published_at': 'data',
                'media_type': 'formato',
                'title': 'legenda_titulo',
                'permalink': 'link'
            })
            logger.info(f"✅ {len(df_top_posts)} Top Posts gerados.")
        else:
            df_top_posts = pd.DataFrame()


        # =====================================================================
        # ETAPA 3: LOAD (GOOGLE SHEETS)
        # =====================================================================
        logger.info("\n📤 ETAPA 3: CARGA NO GOOGLE SHEETS")
        logger.info(f"📑 Sheet ID: {config.google_sheet_id}")
        logger.info(f"📑 Aba Posts: {config.sheet_tab_name}")
        logger.info(f"📑 Aba Analise Hashtag: analise_hashtag")
        logger.info(f"📑 Aba Top Posts: top_posts_mycreator")
        logger.info(f"📑 Aba Crescimento: crescimento_seguidores")
        logger.info(f"📝 Modo: {config.write_mode}")
        
        # Carga 1: Posts (Aba padrão / Dados Brutos)
        success_posts = True
        if not df_final.empty:
            logger.info(f"Uploading Posts ({len(df_final)} linhas)...")
            success_posts = load_to_sheets(df_final, config, tab_name=config.sheet_tab_name)
            time.sleep(5)
            
        # Carga 2: Hashtags 
        success_hashtags = True
        if not df_hashtags_final.empty:
            logger.info(f"Uploading analise_hashtag ({len(df_hashtags_final)} linhas)...")
            success_hashtags = load_to_sheets(df_hashtags_final, config, tab_name="analise_hashtag")
            time.sleep(5)

        # Carga 3: Top Posts
        success_top = True
        if not df_top_posts.empty:
            logger.info(f"Uploading top_posts_mycreator ({len(df_top_posts)} linhas)...")
            success_top = load_to_sheets(df_top_posts, config, tab_name="top_posts_mycreator")
            time.sleep(5)
            
        # Carga 4: Crescimento de Seguidores
        success_growth = True
        if not df_audience_growth.empty:
            logger.info(f"Uploading crescimento_seguidores ({len(df_audience_growth)} linhas)...")
            success_growth = load_to_sheets(df_audience_growth, config, tab_name="crescimento_seguidores")
            time.sleep(5)
        
        if not all([success_posts, success_hashtags, success_top, success_growth]):
            logger.error("❌ Falha parcial na atualização do Google Sheets!")
        else:
            logger.info("✅ Google Sheets (4 abas essenciais) atualizado com sucesso!")
        
        # =====================================================================
        # RESUMO FINAL
        # =====================================================================
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("🏁 ETL CONCLUÍDO COM SUCESSO!")
        logger.info(f"⏱️ Duração: {duration:.2f} segundos")
        logger.info(f"⏱️ Duração: {duration:.2f} segundos")
        logger.info(f"📊 Posts processados: {total_posts}")
        logger.info(f"📄 Sheets: https://docs.google.com/spreadsheets/d/{config.google_sheet_id}")
        logger.info("=" * 60)
        
        # =====================================================================
        # ETAPA 4: ACIONAR GOOGLE APPS SCRIPT
        # =====================================================================
        if config.apps_script_url:
            logger.info("\n🔄 ACIONANDO GOOGLE APPS SCRIPT...")
            logger.info(f"🌐 URL: {config.apps_script_url}")
            try:
                response = requests.get(config.apps_script_url, timeout=30)
                if response.status_code == 200:
                    try:
                        resp_json = response.json()
                        logger.info(f"✅ Google Apps Script executado com sucesso: {resp_json}")
                    except ValueError:
                        logger.info("✅ Google Apps Script executado com sucesso (sem JSON).")
                else:
                    logger.warning(f"⚠️ App Script retornou status HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Erro ao acionar Apps Script: {e}")
                
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erro fatal: {e}")
        return False


if __name__ == "__main__":
    success = run_etl()
    sys.exit(0 if success else 1)
