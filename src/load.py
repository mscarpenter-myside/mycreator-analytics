"""
Módulo de Carga (Load) do ETL.

Responsável por conectar ao Google Sheets e carregar os dados
transformados usando autenticação via Service Account.
"""

import logging
from typing import Optional

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

from .config import Config

logger = logging.getLogger("mycreator_etl")

# Escopos necessários para leitura/escrita no Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


class GoogleSheetsLoader:
    """
    Carregador de dados para Google Sheets.
    
    Usa gspread com autenticação via Service Account para
    ler e escrever dados em planilhas do Google.
    """
    
    def __init__(self, config: Config):
        """
        Inicializa o carregador.
        
        Args:
            config: Configurações do ETL
        """
        self.config = config
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self.worksheet: Optional[gspread.Worksheet] = None
    
    def connect(self) -> bool:
        """
        Estabelece conexão com o Google Sheets.
        
        Returns:
            bool: True se conectou com sucesso
        """
        if not self.config.gcp_credentials:
            logger.error("❌ Credenciais GCP não disponíveis!")
            return False
        
        try:
            logger.info("🔐 Autenticando no Google Sheets...")
            
            # Cria credenciais a partir do JSON
            credentials = Credentials.from_service_account_info(
                self.config.gcp_credentials,
                scopes=SCOPES,
            )
            
            # Inicializa cliente gspread
            self.client = gspread.authorize(credentials)
            
            logger.info("✅ Autenticado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na autenticação: {e}")
            return False
    
    def open_spreadsheet(self, tab_name: str = None) -> bool:
        """
        Abre a planilha e a aba especificadas.
        
        Args:
            tab_name: Nome da aba a abrir (opcional, usa config se None)
            
        Returns:
            bool: True se abriu com sucesso
        """
        if not self.client:
            logger.error("❌ Cliente não conectado! Chame connect() primeiro.")
            return False
            
        target_tab = tab_name or self.config.sheet_tab_name
        
        try:
            logger.info(f"📂 Abrindo planilha: {self.config.google_sheet_id}")
            
            # Abre pelo ID da planilha
            self.spreadsheet = self.client.open_by_key(self.config.google_sheet_id)
            
            logger.info(f"📑 Abrindo aba: {target_tab}")
            
            # Tenta abrir aba existente ou cria nova
            try:
                self.worksheet = self.spreadsheet.worksheet(target_tab)
            except gspread.WorksheetNotFound:
                logger.info(f"📝 Aba não existe. Criando: {target_tab}")
                self.worksheet = self.spreadsheet.add_worksheet(
                    title=target_tab,
                    rows=1000,
                    cols=26,
                )
            
            logger.info("✅ Planilha aberta com sucesso!")
            return True
            
        except gspread.SpreadsheetNotFound:
            logger.error(f"❌ Planilha não encontrada: {self.config.google_sheet_id}")
            logger.error("Verifique se o ID está correto e se a Service Account tem acesso.")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao abrir planilha: {e}")
            return False
    
    def load(self, df: pd.DataFrame) -> bool:
        """
        Carrega DataFrame na planilha.
        
        Args:
            df: DataFrame com dados a carregar
            
        Returns:
            bool: True se carregou com sucesso
        """
        if df.empty:
            logger.warning("⚠️ DataFrame vazio. Nada a carregar.")
            return True
        
        if not self.worksheet:
            logger.error("❌ Worksheet não aberta! Chame open_spreadsheet() primeiro.")
            return False
        
        try:
            # Converte DataFrame para lista de listas
            data = self._dataframe_to_sheets_format(df)
            
            if self.config.write_mode == "overwrite":
                return self._write_overwrite(data)
            else:
                return self._write_append(data)
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def _dataframe_to_sheets_format(self, df: pd.DataFrame) -> list[list]:
        """
        Converte DataFrame para formato do Google Sheets.
        
        Args:
            df: DataFrame pandas
            
        Returns:
            list[list]: Dados em formato de lista de listas
        """
        # Substitui NaN por string vazia
        df = df.fillna("")
        
        # Converte valores para tipos serializáveis
        df = df.astype(str)
        
        # Header + dados
        header = df.columns.tolist()
        rows = df.values.tolist()
        
        return [header] + rows
    
    def _write_overwrite(self, data: list[list]) -> bool:
        """
        Escreve dados sobrescrevendo conteúdo existente.
        
        Args:
            data: Dados a escrever (com header)
            
        Returns:
            bool: True se escreveu com sucesso
        """
        logger.info(f"📝 Escrevendo {len(data) - 1} linhas (modo: overwrite)...")
        
        try:
            # Limpa toda a planilha
            self.worksheet.clear()
            
            # Escreve dados
            self.worksheet.update(
                range_name="A1",
                values=data,
                value_input_option="USER_ENTERED",
            )
            
            # Formata header
            self._format_header()
            
            logger.info("✅ Dados escritos com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao escrever (overwrite): {e}")
            return False
    
    def _write_append(self, data: list[list]) -> bool:
        """
        Adiciona dados ao final da planilha.
        
        Args:
            data: Dados a escrever (com header)
            
        Returns:
            bool: True se escreveu com sucesso
        """
        logger.info(f"📝 Adicionando {len(data) - 1} linhas (modo: append)...")
        
        try:
            # Verifica se a planilha está vazia (precisa do header)
            existing_data = self.worksheet.get_all_values()
            
            if not existing_data:
                # Planilha vazia - escreve com header
                rows_to_write = data
            else:
                # Planilha tem dados - escreve só os dados (sem header)
                rows_to_write = data[1:]
            
            # Adiciona ao final
            self.worksheet.append_rows(
                values=rows_to_write,
                value_input_option="USER_ENTERED",
                insert_data_option="INSERT_ROWS",
            )
            
            logger.info("✅ Dados adicionados com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao escrever (append): {e}")
            return False
    
    def _format_header(self):
        """Aplica formatação no header da planilha."""
        try:
            # Formata primeira linha (header)
            self.worksheet.format("1:1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                "horizontalAlignment": "CENTER",
            })
            
            # Congela primeira linha
            self.worksheet.freeze(rows=1)
            
        except Exception as e:
            logger.debug(f"Não foi possível formatar header: {e}")
    
    def get_row_count(self) -> int:
        """
        Retorna número de linhas com dados na planilha.
        
        Returns:
            int: Número de linhas
        """
        if not self.worksheet:
            return 0
        
        try:
            return len(self.worksheet.get_all_values())
        except Exception:
            return 0
    
    def close(self):
        """Fecha conexões (cleanup)."""
        self.worksheet = None
        self.spreadsheet = None
        self.client = None
        logger.debug("🔌 Conexões fechadas")


def load_to_sheets(df: pd.DataFrame, config: Config, tab_name: str = None) -> bool:
    """
    Função helper para carregar dados no Google Sheets.
    
    Args:
        df: DataFrame com dados
        config: Configurações do ETL
        tab_name: Nome da aba (opcional)
        
    Returns:
        bool: True se carregou com sucesso
    """
    loader = GoogleSheetsLoader(config)
    
    try:
        # Conecta
        if not loader.connect():
            return False
        
        # Abre planilha
        if not loader.open_spreadsheet(tab_name):
            return False
        
        # Carrega dados
        return loader.load(df)
        
    finally:
        loader.close()
