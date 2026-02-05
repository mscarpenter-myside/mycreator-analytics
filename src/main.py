"""
MyCreator Analytics ETL - Script Principal

Orquestra o pipeline ETL completo:
1. Extract: Busca dados da API MyCreator (4 workspaces fixos)
2. Transform: Converte PostData para DataFrame pandas
3. Load: Exporta para Excel consolidado

Workspaces Alvo:
- Florianópolis
- Florianópolis Continente  
- Goiânia
- MyCreator
"""

import logging
import sys
from datetime import datetime
from dataclasses import asdict

import pandas as pd

from .config import get_config, setup_logging
from .extract import MyCreatorExtractor, TARGET_WORKSPACES


def run_etl():
    """Executa o pipeline ETL completo."""
    
    # Setup
    config = get_config()
    logger = setup_logging(debug=config.debug_mode)
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO ETL MyCreator Analytics")
    logger.info(f"📅 Data/Hora: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🎯 Workspaces: {len(TARGET_WORKSPACES)} cidades")
    logger.info("=" * 60)
    
    try:
        # =====================================================================
        # ETAPA 1: EXTRACT
        # =====================================================================
        logger.info("\n📡 ETAPA 1: EXTRAÇÃO")
        extractor = MyCreatorExtractor(config)
        
        # Extrai de todos os workspaces definidos em TARGET_WORKSPACES
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
            df_final = df_final.sort_values(
                by=["Cidade", "Data Publicação"], 
                ascending=[True, False]
            )
        
        # Estatísticas
        total_posts = len(df_final)
        total_likes = df_final["Likes"].sum() if "Likes" in df_final.columns else 0
        total_reach = df_final["Alcance"].sum() if "Alcance" in df_final.columns else 0
        
        logger.info(f"📊 Total: {total_posts} posts")
        logger.info(f"❤️ Likes: {total_likes:,}")
        logger.info(f"👁️ Alcance: {total_reach:,}")
        
        # =====================================================================
        # ETAPA 3: LOAD (EXCEL)
        # =====================================================================
        logger.info("\n📤 ETAPA 3: EXPORTAÇÃO")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Relatorio_Analytics_{timestamp}.xlsx"
        
        # Salva Excel com formatação
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_final.to_excel(writer, sheet_name="Dados_Brutos", index=False)
            
            # Ajusta largura das colunas
            worksheet = writer.sheets["Dados_Brutos"]
            for idx, col in enumerate(df_final.columns):
                try:
                    max_length = max(
                        df_final[col].astype(str).str.len().max(),
                        len(str(col))
                    ) + 2
                    col_letter = chr(65 + idx) if idx < 26 else f"{chr(64 + idx // 26)}{chr(65 + idx % 26)}"
                    worksheet.column_dimensions[col_letter].width = min(max_length, 50)
                except Exception:
                    pass
        
        logger.info(f"✅ Arquivo gerado: {filename}")
        
        # =====================================================================
        # RESUMO FINAL
        # =====================================================================
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("🏁 ETL CONCLUÍDO COM SUCESSO!")
        logger.info(f"⏱️ Duração: {duration:.2f} segundos")
        logger.info(f"📊 Posts processados: {total_posts}")
        logger.info(f"📂 Arquivo: {filename}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erro fatal: {e}")
        return False


def main():
    """Ponto de entrada principal."""
    try:
        success = run_etl()
        sys.exit(0 if success else 1)
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()