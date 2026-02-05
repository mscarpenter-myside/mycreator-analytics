#!/usr/bin/env python3
"""Verifica se o Google Sheets foi atualizado."""
from src.config import get_config
from src.load import GoogleSheetsLoader

config = get_config()
loader = GoogleSheetsLoader(config)

if loader.connect() and loader.open_spreadsheet():
    # Lê primeira linha (header)
    header = loader.worksheet.row_values(1)
    print("=" * 60)
    print("VERIFICAÇÃO DO GOOGLE SHEETS")
    print("=" * 60)
    print(f"\n📊 COLUNAS NO SHEETS ({len(header)} total):\n")
    for i, col in enumerate(header, 1):
        marker = "🏙️" if col == "Cidade" else ("🕐" if col == "Timestamp de Atualização" else "  ")
        print(f"   {marker} {i:2}. {col}")
    
    print(f"\n✅ Primeira coluna: {header[0]}")
    print(f"✅ Última coluna: {header[-1]}")
    
    # Total de linhas
    rows = loader.get_row_count()
    print(f"\n📈 Total de linhas (incluindo header): {rows}")
    
    # Amostra da última coluna (timestamp)
    if "Timestamp de Atualização" in header:
        last_col_idx = header.index("Timestamp de Atualização") + 1
        sample = loader.worksheet.cell(2, last_col_idx).value
        print(f"\n🕐 Amostra de Timestamp: {sample}")
else:
    print("❌ Erro ao conectar")
