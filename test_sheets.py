#!/usr/bin/env python3
"""Teste rápido de conexão com Google Sheets."""
from src.config import get_config
from src.load import GoogleSheetsLoader

config = get_config()
print(f"Sheet ID: {config.google_sheet_id}")
print(f"Tab Name: {config.sheet_tab_name}")
print(f"GCP Credentials: {'Loaded' if config.gcp_credentials else 'MISSING!'}")

if config.gcp_credentials:
    print(f"Service Account: {config.gcp_credentials.get('client_email', 'N/A')}")

loader = GoogleSheetsLoader(config)
if loader.connect():
    print("✅ Conexão GCP OK!")
    if loader.open_spreadsheet():
        print("✅ Planilha aberta!")
        rows = loader.get_row_count()
        print(f"📊 Linhas atuais na aba: {rows}")
    else:
        print("❌ Erro ao abrir planilha")
else:
    print("❌ Erro na conexão")
