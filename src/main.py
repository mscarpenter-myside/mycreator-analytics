"""
MyCreator Analytics ETL - Script Principal

Este é o "maestro" que orquestra todo o pipeline ETL:
1. Extract: Busca dados da API MyCreator
2. Transform: Limpa, calcula métricas e formata dados
3. Load: Envia para Google Sheets
"""

import sys
import logging
from datetime import datetime

from .config import get_config, setup_logging, Config
from .extract import MyCreatorExtractor
from .transform import DataTransformer
from .load import load_to_sheets


def run_etl(config: Config, logger: logging.Logger) -> bool:
    """Executa o pipeline ETL completo."""
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO ETL MyCreator Analytics")
    logger.info(f"📅 Data/Hora: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # ETAPA 1: EXTRACT
        logger.info("\n📡 ETAPA 1: EXTRAÇÃO")
        extractor = MyCreatorExtractor(config)
        posts = extractor.extract_all()
        
        if not posts:
            logger.warning("⚠️ Nenhum post extraído.")
            return False
        
        # ETAPA 2: TRANSFORM
        logger.info("\n🔄 ETAPA 2: TRANSFORMAÇÃO")
        transformer = DataTransformer()
        df = transformer.transform(posts)
        
        if df.empty:
            logger.warning("⚠️ DataFrame vazio.")
            return False
        
        summary = transformer.get_summary(df)
        logger.info(f"📊 Posts: {summary['total_posts']} | Likes: {summary['total_likes']:,}")
        
        # ETAPA 3: LOAD
        logger.info("\n📤 ETAPA 3: CARGA")
        success = load_to_sheets(df, config)
        
        if not success:
            return False
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n✅ ETL CONCLUÍDO em {duration:.2f}s - {len(df)} registros")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erro: {e}")
        return False


def main():
    """Ponto de entrada principal."""
    try:
        config = get_config()
        logger = setup_logging(debug=config.debug_mode)
        success = run_etl(config, logger)
        sys.exit(0 if success else 1)
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
