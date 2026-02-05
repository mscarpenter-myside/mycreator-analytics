#!/usr/bin/env python3
"""
Executa o ETL completo:
1. Extract: Busca dados da API MyCreator (4 workspaces)
2. Transform: Converte PostData para DataFrame pandas
3. Load: Carrega no Google Sheets (não Excel local!)
"""
import logging
import sys
from datetime import datetime
from dataclasses import asdict

import pandas as pd

from src.config import get_config, setup_logging
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES
from src.load import load_to_sheets

# Setup
config = get_config()
logger = setup_logging(debug=config.debug_mode)
start_time = datetime.now()

logger.info("=" * 60)
logger.info("🚀 INICIANDO ETL MyCreator Analytics")
logger.info(f"📅 Data/Hora: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"🎯 Workspaces: {len(TARGET_WORKSPACES)} cidades")
logger.info(f"📊 Google Sheet ID: {config.google_sheet_id}")
logger.info("=" * 60)

# =========================================================================
# ETAPA 1: EXTRACT
# =========================================================================
logger.info("\n📡 ETAPA 1: EXTRAÇÃO")
extractor = MyCreatorExtractor(config)
all_posts = extractor.extract_from_workspaces()

if not all_posts:
    logger.warning("⚠️ Nenhum post extraído.")
    sys.exit(1)

# =========================================================================
# ETAPA 2: TRANSFORM
# =========================================================================
logger.info("\n🔄 ETAPA 2: TRANSFORMAÇÃO")
records = [asdict(post) for post in all_posts]
df = pd.DataFrame(records)

# Mapeamento de colunas para nomes amigáveis
column_mapping = {
    "workspace_name": "Cidade",
    "published_at": "Data Publicação",
    "platform": "Rede Social",
    "profile_name": "Perfil",
    "post_type": "Tipo",
    "title": "Título",
    "caption": "Legenda",
    "likes": "Likes",
    "comments": "Comentários",
    "saves": "Salvos",
    "shares": "Compartilhamentos",
    "reach": "Alcance",
    "impressions": "Impressões",
    "plays": "Plays",
    "engagement_rate": "Taxa Engajamento (%)",
    "permalink": "Link",
    "external_id": "ID Instagram",
    "internal_id": "ID Interno",
    "analytics_error": "Status Dados"
}

# Seleciona e renomeia colunas
columns_to_export = [col for col in column_mapping.keys() if col in df.columns]
df_final = df[columns_to_export].rename(columns=column_mapping)

# Ordena por cidade e data
if "Data Publicação" in df_final.columns:
    df_final = df_final.sort_values(by=["Cidade", "Data Publicação"], ascending=[True, False])

# Estatísticas
total_posts = len(df_final)
total_likes = df_final["Likes"].sum() if "Likes" in df_final.columns else 0
total_reach = df_final["Alcance"].sum() if "Alcance" in df_final.columns else 0

logger.info(f"📊 Total: {total_posts} posts")
logger.info(f"❤️ Likes: {total_likes:,}")
logger.info(f"👁️ Alcance: {total_reach:,}")

# =========================================================================
# ETAPA 3: LOAD (GOOGLE SHEETS)
# =========================================================================
logger.info("\n📤 ETAPA 3: CARGA NO GOOGLE SHEETS")
logger.info(f"📑 Aba destino: {config.sheet_tab_name}")
logger.info(f"📝 Modo: {config.write_mode}")

success = load_to_sheets(df_final, config)

if not success:
    logger.error("❌ Falha ao carregar dados no Google Sheets!")
    sys.exit(1)

# =========================================================================
# RESUMO FINAL
# =========================================================================
duration = (datetime.now() - start_time).total_seconds()

logger.info("\n" + "=" * 60)
logger.info("🏁 ETL CONCLUÍDO COM SUCESSO!")
logger.info(f"⏱️ Duração: {duration:.2f} segundos")
logger.info(f"📊 Posts carregados: {total_posts}")
logger.info(f"📑 Planilha: https://docs.google.com/spreadsheets/d/{config.google_sheet_id}")
logger.info("=" * 60)
