"""
Módulo de Banco de Dados (PostgreSQL/Supabase e SQLite) do ETL.

Responsável por gerenciar a persistência dos dados enriquecidos
em nuvem (Supabase) para acesso compartilhado.
"""

import logging
import socket
import pandas as pd
from sqlalchemy import create_engine
import sqlite3

# Força IPv4 para compatibilidade com WSL
original_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

logger = logging.getLogger("mycreator_etl")

class SupabaseDatabase:
    """Gerenciador do banco de dados PostgreSQL no Supabase."""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.engine = None

    def connect(self):
        """Estabelece conexão com o Supabase."""
        try:
            self.engine = create_engine(self.uri)
            logger.info("📡 Conectado ao Supabase (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao Supabase: {e}")
            raise

    def save_posts(self, df: pd.DataFrame, table_name: str = "posts_final"):
        """
        Salva o DataFrame no Supabase.
        Usa 'replace' para garantir a versão mais atualizada.
        """
        if df.empty:
            logger.warning("⚠️ DataFrame vazio. Nada para salvar no Supabase.")
            return

        try:
            if not self.engine:
                self.connect()
            
            # Salva no banco via SQLAlchemy
            df.to_sql(table_name, self.engine, if_exists="replace", index=False)
            logger.info(f"✅ {len(df)} registros salvos na tabela '{table_name}' do Supabase.")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar dados no Supabase: {e}")
            raise

    def close(self):
        """Fecha a conexão (SQLAlchemy gerencia o pool, mas deixamos p/ compatibilidade)."""
        if self.engine:
            self.engine.dispose()
            logger.debug("🔌 Conexão Supabase encerrada")


class SQLiteDatabase:
    """Gerenciador do banco de dados SQLite (Local)."""
    
    def __init__(self, db_path: str = "mycreator.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Estabelece conexão com o SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"🗄️ Conectado ao SQLite: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao SQLite: {e}")
            raise

    def save_posts(self, df: pd.DataFrame, table_name: str = "posts_final"):
        """Salva o DataFrame no SQLite."""
        if df.empty:
            return

        try:
            if not self.conn:
                self.connect()
            df.to_sql(table_name, self.conn, if_exists="replace", index=False)
            logger.info(f"✅ {len(df)} registros salvos na tabela '{table_name}' do SQLite.")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar dados no SQLite: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()
