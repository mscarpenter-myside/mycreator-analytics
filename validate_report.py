import pandas as pd
df = pd.read_excel("Relatorio_MyCreator_20260204_2210.xlsx")
print("=" * 70)
print("VALIDAÇÃO FINAL - VERSÃO DIRETORIA")
print("=" * 70)

print(f"\n📊 COLUNAS (na ordem exata):\n")
for i, col in enumerate(df.columns, 1):
    marker = "🏙️" if col == "Cidade" else ("🕐" if col == "Timestamp de Atualização" else "  ")
    print(f"   {marker} {i:2}. {col}")

print(f"\n📈 TOTAL DE LINHAS: {len(df)}")

print("\n✅ VERIFICAÇÕES:")
print(f"   1ª coluna = 'Cidade': {df.columns[0] == 'Cidade'}")
print(f"   2ª coluna = 'Data de Publicação': {df.columns[1] == 'Data de Publicação'}")
print(f"   Última coluna = 'Timestamp de Atualização': {df.columns[-1] == 'Timestamp de Atualização'}")

print("\n📍 CIDADES EXTRAÍDAS:")
for cidade in df['Cidade'].unique():
    count = len(df[df['Cidade'] == cidade])
    print(f"   • {cidade}: {count} posts")

print("\n📅 FORMATO DA DATA DE PUBLICAÇÃO:")
print(f"   Exemplo: {df['Data de Publicação'].iloc[0]}")

print("\n🕐 FORMATO DO TIMESTAMP DE ATUALIZAÇÃO:")
print(f"   Exemplo: {df['Timestamp de Atualização'].iloc[0]}")

print("\n📋 AMOSTRA (primeiras 2 linhas):")
cols = ["Cidade", "Data de Publicação", "Perfil", "Likes", "Alcance", "Timestamp de Atualização"]
print(df[cols].head(2).to_string())
