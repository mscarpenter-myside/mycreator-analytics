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
import logging
import sys
from datetime import datetime
from dataclasses import asdict

import pandas as pd

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
            return False
        
        # =====================================================================
        # ETAPA 2: TRANSFORM
        # =====================================================================
        logger.info("\n🔄 ETAPA 2: TRANSFORMAÇÃO")
        
        # Converte lista de dataclass para DataFrame
        records = [asdict(post) for post in all_posts]
        df = pd.DataFrame(records)
        
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
            "post_type": "Tipo",  # REELS, FEED, STORY
            
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
            
            # TÉCNICO (última: Timestamp de Atualização)
            "permalink": "Link",
            "external_id": "ID Instagram",
            "internal_id": "ID Interno",
            "analytics_error": "Status Dados",
            "extraction_timestamp": "Timestamp de Atualização",
        }
        
        # Seleciona e renomeia colunas existentes (preserva ordem do dict)
        columns_to_export = [col for col in column_mapping.keys() if col in df.columns]
        df_final = df[columns_to_export].rename(columns=column_mapping)
        
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
        
        logger.info(f"📊 Total: {total_posts} posts")
        logger.info(f"❤️ Likes: {total_likes:,}")
        logger.info(f"👁️ Alcance: {total_reach:,}")
        logger.info(f"💬 Comentários: {total_comments:,}")
        
        # Resumo por cidade
        logger.info("\n📈 RESUMO POR CIDADE:")
        for cidade in df_final["Cidade"].unique():
            df_cidade = df_final[df_final["Cidade"] == cidade]
            logger.info(f"   • {cidade}: {len(df_cidade)} posts | {int(df_cidade['Likes'].sum())} likes")
        
        # =====================================================================
        # ETAPA 3: LOAD (GOOGLE SHEETS)
        # =====================================================================
        logger.info("\n📤 ETAPA 3: CARGA NO GOOGLE SHEETS")
        logger.info(f"📑 Sheet ID: {config.google_sheet_id}")
        logger.info(f"📑 Aba: {config.sheet_tab_name}")
        logger.info(f"📝 Modo: {config.write_mode}")
        
        sheets_success = load_to_sheets(df_final, config)
        
        if not sheets_success:
            logger.error("❌ Falha ao atualizar Google Sheets!")
            return False
        
        logger.info("✅ Google Sheets atualizado com sucesso!")
        
        # =====================================================================
        # RESUMO FINAL
        # =====================================================================
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("🏁 ETL CONCLUÍDO COM SUCESSO!")
        logger.info(f"⏱️ Duração: {duration:.2f} segundos")
        logger.info(f"📊 Posts processados: {total_posts}")
        logger.info(f"📄 Sheets: https://docs.google.com/spreadsheets/d/{config.google_sheet_id}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erro fatal: {e}")
        return False


if __name__ == "__main__":
    success = run_etl()
    sys.exit(0 if success else 1)
