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
from src.load import load_to_sheets, get_sheet_data
from src.database import SupabaseDatabase


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
            logger.warning("⚠️ Nada novo extraído nesta rodada. Prosseguindo para verificar sincronização cloud...")
        
        # Converte para DataFrame mesmo se estiver vazio para evitar erros abaixo
        
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
            "engagement_rate": "taxa_engajamento",
            
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
        
        # Garante que as colunas existam antes do mapeamento para evitar erros
        for col in ["reach", "engagement_rate", "reach_rate", "follower_count"]:
            if col not in df_posts.columns:
                df_posts[col] = 0
        
        # Seleciona e renomeia colunas (preserva a ordem abaixo)
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
        # 10. TOP POSTS GERAL (ContentStudio + Orgânicos da aba Analytics)
        # =========================================================================

        # --- 10.1 Top Posts do ContentStudio (via fetchPlans) ---
        if not df_posts.empty:
            interaction_cols = ['likes', 'comments', 'shares', 'saves']
            actual_cols = [c for c in interaction_cols if c in df_posts.columns]
            df_posts['engagement_total'] = df_posts[actual_cols].fillna(0).sum(axis=1) if actual_cols else 0

            top_reach = df_posts.nlargest(50, 'reach')[['permalink', 'reach', 'title', 'profile_name', 'workspace_name', 'published_at', 'media_type', 'external_id']].copy()
            top_reach['Rank_Tipo'] = 'alcance'
            top_reach = top_reach.rename(columns={'reach': 'Valor_Metrica'})

            top_engage = df_posts.nlargest(50, 'engagement_total')[['permalink', 'engagement_total', 'title', 'profile_name', 'workspace_name', 'published_at', 'media_type', 'external_id']].copy()
            top_engage['Rank_Tipo'] = 'engajamento'
            top_engage = top_engage.rename(columns={'engagement_total': 'Valor_Metrica'})

            top_impressions = df_posts.nlargest(50, 'impressions')[['permalink', 'impressions', 'title', 'profile_name', 'workspace_name', 'published_at', 'media_type', 'external_id']].copy()
            top_impressions['Rank_Tipo'] = 'impressoes'
            top_impressions = top_impressions.rename(columns={'impressions': 'Valor_Metrica'})

            df_top_cs = pd.concat([top_reach, top_engage, top_impressions])
            df_top_cs['Valor_Metrica'] = df_top_cs['Valor_Metrica'].astype(int)
            df_top_cs = df_top_cs[['Rank_Tipo', 'Valor_Metrica', 'profile_name', 'workspace_name', 'published_at', 'media_type', 'title', 'permalink', 'external_id']]
            df_top_cs = df_top_cs.rename(columns={
                'Rank_Tipo': 'rank_tipo',
                'Valor_Metrica': 'valor_metrica',
                'profile_name': 'perfil',
                'workspace_name': 'workspace',
                'published_at': 'data',
                'media_type': 'formato',
                'title': 'legenda_titulo',
                'permalink': 'link',
                'external_id': 'id_post',
            })
            df_top_cs['data'] = pd.to_datetime(df_top_cs['data'], errors='coerce').dt.strftime("%d/%m/%Y")
            df_top_cs['fonte'] = 'mycreator'

            # IDs dos posts ContentStudio para cruzamento com Analytics
            mycreator_external_ids = set(df_posts['external_id'].dropna().astype(str))
        else:
            df_top_cs = pd.DataFrame()
            mycreator_external_ids = set()

        # --- 10.2 Top Posts da aba Analytics (orgânicos + ContentStudio) ---
        logger.info("\n🏆 PROCESSANDO TOP POSTS ANALYTICS...")

        now_brt = datetime.now()
        analytics_date_range = f"2021-01-01 - {now_brt.strftime('%Y-%m-%d')}"

        METRIC_TYPES = [
            ("alcance",     "reach"),
            ("engajamento", "total_engagement"),
            ("impressoes",  "impressions"),
        ]

        analytics_rows = []
        for ws in TARGET_WORKSPACES:
            posts_analytics = extractor.fetch_analytics_top_posts(
                ws["id"], ws["name"], analytics_date_range
            )
            for p in posts_analytics:
                ext_id = str(p.get("external_id", ""))
                fonte = "mycreator" if ext_id and ext_id in mycreator_external_ids else "instagram_nativo"

                published_raw = p.get("published_at", "")
                try:
                    data_fmt = pd.to_datetime(published_raw, errors='coerce').strftime("%d/%m/%Y")
                except Exception:
                    data_fmt = str(published_raw)[:10] if published_raw else ""

                base = {
                    "perfil":         p.get("profile_name", ""),
                    "workspace":      ws["name"],
                    "data":           data_fmt,
                    "formato":        p.get("media_type", ""),
                    "legenda_titulo": (p.get("caption", "") or "")[:100],
                    "link":           p.get("permalink", ""),
                    "fonte":          fonte,
                    "id_post":        ext_id,
                }
                for rank_tipo_label, metric_col in METRIC_TYPES:
                    analytics_rows.append({
                        **base,
                        "rank_tipo":     rank_tipo_label,
                        "valor_metrica": int(p.get(metric_col, 0) or 0),
                    })

        df_top_analytics = pd.DataFrame(analytics_rows) if analytics_rows else pd.DataFrame()

        # --- 10.3 Combina ContentStudio + Analytics e rankeia Top 20 por fonte por tipo ---
        frames = [f for f in [df_top_cs, df_top_analytics] if not f.empty]
        if frames:
            df_combined = pd.concat(frames, ignore_index=True)

            # Remove duplicatas por (link, rank_tipo, fonte, workspace) mantendo o maior valor
            df_combined = df_combined.sort_values('valor_metrica', ascending=False)
            df_combined = df_combined.drop_duplicates(subset=['link', 'rank_tipo', 'fonte', 'workspace'], keep='first')

            # top 5 por perfil por workspace por métrica — para ambas as fontes
            slices = []
            for rank_tipo in ['alcance', 'engajamento', 'impressoes']:
                for ws_name in df_combined['workspace'].dropna().unique():
                    for fonte in ['mycreator', 'instagram_nativo']:
                        mask = (
                            (df_combined['workspace'] == ws_name) &
                            (df_combined['rank_tipo'] == rank_tipo) &
                            (df_combined['fonte'] == fonte)
                        )
                        for perfil in df_combined[mask]['perfil'].dropna().unique():
                            subset = df_combined[mask & (df_combined['perfil'] == perfil)]
                            top5 = subset.nlargest(5, 'valor_metrica')
                            if not top5.empty:
                                slices.append(top5)

            df_top_posts = pd.concat(slices, ignore_index=True)

            # Garante colunas na ordem correta
            df_top_posts = df_top_posts[['rank_tipo', 'fonte', 'workspace', 'valor_metrica', 'perfil', 'data', 'formato', 'legenda_titulo', 'link', 'id_post']]

            # Normaliza valores da coluna formato
            df_top_posts['formato'] = df_top_posts['formato'].replace('CAROUSEL_ALBUM', 'Carousel')

            n_organico = (df_top_posts['fonte'] == 'instagram_nativo').sum()
            n_mycreator = (df_top_posts['fonte'] == 'mycreator').sum()
            logger.info(f"✅ {len(df_top_posts)} Top Posts gerados → {n_mycreator} mycreator | {n_organico} instagram_nativo")
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

        # Carga 3a: Top Posts MyCreator
        success_top = True
        if not df_top_posts.empty:
            df_mycreator_top = df_top_posts[df_top_posts['fonte'] == 'mycreator'].copy()
            df_nativo_top    = df_top_posts[df_top_posts['fonte'] == 'instagram_nativo'].copy()

            if not df_mycreator_top.empty:
                logger.info(f"Uploading top_posts_mycreator ({len(df_mycreator_top)} linhas)...")
                success_top = load_to_sheets(df_mycreator_top, config, tab_name="top_posts_mycreator")
                time.sleep(5)

            if not df_nativo_top.empty:
                logger.info(f"Uploading top_post_nativo ({len(df_nativo_top)} linhas)...")
                success_top = load_to_sheets(df_nativo_top, config, tab_name="top_post_nativo") and success_top
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
            logger.info("\n🔄 ETAPA 4: ACIONANDO GOOGLE APPS SCRIPT (CONSOLIDAÇÃO)...")
            logger.info(f"🌐 URL: {config.apps_script_url}")
            try:
                # Aumentamos o timeout para 60s pois o GAS pode ser lento para consolidar
                response = requests.get(config.apps_script_url, timeout=60, allow_redirects=True)
                if response.status_code == 200:
                    try:
                        resp_json = response.json()
                        logger.info(f"✅ Google Apps Script executado com sucesso: {resp_json}")
                    except ValueError:
                        logger.info("✅ Google Apps Script executado com sucesso (sem JSON).")
                    
                    # Wait for GAS to complete (5-10 seconds as planned)
                    logger.info("⏳ Aguardando 15s para consolidação finalizar no Google...")
                    time.sleep(15)
                else:
                    logger.warning(f"⚠️ Google Apps Script retornou status HTTP {response.status_code}")
                    logger.warning("⚠️ Prosseguindo para sincronização com dados possivelmente desatualizados.")
            except Exception as e:
                logger.error(f"❌ Erro ao acionar Apps Script: {e}")
        # =====================================================================
        # ETAPA 5: FETCH CONSOLIDATED DATA & SAVE TO SUPABASE
        # =====================================================================
        logger.info("\n🗄️ ETAPA 5: SINCRONIZAÇÃO CLOUD (SUPABASE)")
        
        try:
            # 5.1 Sincronizar Posts Consolidados
            df_consolidated = get_sheet_data(config, "base_looker_studio_posts")
            
            if not df_consolidated.empty:
                logger.info(f"🧹 Limpando e formatando posts para Supabase...")
                
                cols_to_clean = ["curtidas", "comentarios", "salvos", "compartilhamentos", "alcance"]
                cols_rate = ["taxa_engajamento", "taxa_alcance"]
                
                for col in cols_to_clean:
                    if col in df_consolidated.columns:
                        df_consolidated[col] = pd.to_numeric(
                            df_consolidated[col].astype(str).str.replace(".", "").replace("", "0"), 
                            errors='coerce'
                        ).fillna(0).astype(int)
                        
                for col in cols_rate:
                    if col in df_consolidated.columns:
                        def clean_rate(val):
                            if not val: return 0.0
                            val_str = str(val).replace("%", "").replace(",", ".").strip()
                            try:
                                f_val = float(val_str)
                                if "%" in str(val) or f_val > 1.0:
                                    return round(f_val / 100, 4)
                                return round(f_val, 4)
                            except:
                                return 0.0
                        df_consolidated[col] = df_consolidated[col].apply(clean_rate)
                
                db = SupabaseDatabase(config.supabase_uri)
                db.save_posts(df_consolidated, table_name="posts_final")
                db.close()
                logger.info(f"✅ SUCESSO: {len(df_consolidated)} posts sincronizados no Supabase (tabela: posts_final).")
            else:
                logger.warning("⚠️ Não foi possível ler a aba 'base_looker_studio_posts'.")

            # 5.2 Sincronizar Histórico de Seguidores (NOVO)
            df_growth_sheet = get_sheet_data(config, "crescimento_seguidores")
            if not df_growth_sheet.empty:
                logger.info(f"🧹 Limpando e formatando histórico de seguidores p/ Supabase...")
                
                # Converte colunas numéricas do crescimento
                numeric_growth_cols = ["seguidores", "variacao_diaria"]
                for col in numeric_growth_cols:
                    if col in df_growth_sheet.columns:
                        df_growth_sheet[col] = pd.to_numeric(
                            df_growth_sheet[col].astype(str).str.replace(".", ""), 
                            errors='coerce'
                        ).fillna(0).astype(int)
                
                db = SupabaseDatabase(config.supabase_uri)
                db.save_posts(df_growth_sheet, table_name="seguidores_history")
                db.close()
                logger.info(f"✅ SUCESSO: {len(df_growth_sheet)} linhas de histórico sincronizadas no Supabase (tabela: seguidores_history).")
            else:
                logger.warning("⚠️ Não foi possível ler a aba 'crescimento_seguidores'.")
        
        except Exception as e:
            logger.error(f"❌ Erro crítico na sincronização Supabase: {e}")
                
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erro fatal: {e}")
        return False


if __name__ == "__main__":
    success = run_etl()
    sys.exit(0 if success else 1)
