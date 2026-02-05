#!/usr/bin/env python3
"""Verifica valores das colunas corrigidas."""
from src.config import get_config
from src.load import GoogleSheetsLoader

config = get_config()
loader = GoogleSheetsLoader(config)

if loader.connect() and loader.open_spreadsheet():
    print("=" * 60)
    print("VERIFICAÇÃO DOS CAMPOS CORRIGIDOS")
    print("=" * 60)
    
    # Lê header e algumas linhas
    header = loader.worksheet.row_values(1)
    row2 = loader.worksheet.row_values(2)
    row3 = loader.worksheet.row_values(3)
    
    # Índices das colunas que queremos verificar
    cols_to_check = ["Rede Social", "Tipo", "Título"]
    
    for col_name in cols_to_check:
        if col_name in header:
            idx = header.index(col_name)
            val2 = row2[idx] if len(row2) > idx else "N/A"
            val3 = row3[idx] if len(row3) > idx else "N/A"
            print(f"\n📌 {col_name}:")
            print(f"   Linha 2: {val2[:60]}..." if len(str(val2)) > 60 else f"   Linha 2: {val2}")
            print(f"   Linha 3: {val3[:60]}..." if len(str(val3)) > 60 else f"   Linha 3: {val3}")
        else:
            print(f"\n❌ Coluna '{col_name}' não encontrada")
    
    # Mostra primeiras 5 linhas das colunas chave
    print("\n" + "=" * 60)
    print("AMOSTRA COMPLETA (5 primeiras linhas)")
    print("=" * 60)
    
    all_values = loader.worksheet.get_all_values()
    
    # Índices
    cidade_idx = header.index("Cidade") if "Cidade" in header else 0
    rede_idx = header.index("Rede Social") if "Rede Social" in header else 2
    tipo_idx = header.index("Tipo") if "Tipo" in header else 4
    titulo_idx = header.index("Título") if "Título" in header else 5
    
    print(f"\n{'Cidade':<20} {'Rede Social':<15} {'Tipo':<10} {'Título':<40}")
    print("-" * 85)
    
    for i, row in enumerate(all_values[1:6], 1):  # Skip header, show 5 rows
        cidade = row[cidade_idx] if len(row) > cidade_idx else ""
        rede = row[rede_idx] if len(row) > rede_idx else ""
        tipo = row[tipo_idx] if len(row) > tipo_idx else ""
        titulo = row[titulo_idx][:37] + "..." if len(row) > titulo_idx and len(row[titulo_idx]) > 40 else row[titulo_idx] if len(row) > titulo_idx else ""
        
        print(f"{cidade:<20} {rede:<15} {tipo:<10} {titulo:<40}")
else:
    print("❌ Erro ao conectar")
