#!/usr/bin/env python3
"""Script de teste rápido do ETL."""
from src.config import get_config
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES

config = get_config()
extractor = MyCreatorExtractor(config)

print("Workspaces alvo:", [ws["name"] for ws in TARGET_WORKSPACES])

# Testa apenas 1 workspace
ws = TARGET_WORKSPACES[0]
print(f"\nTestando {ws['name']}...")
plans = extractor.fetch_posts_list(ws["id"])
print(f"Posts encontrados: {len(plans)}")

if plans:
    print(f"Primeiro post ID: {plans[0].get('_id')}")
    
    # Testa detalhes
    details = extractor.fetch_plan_details(plans[0]["_id"], ws["id"])
    if details:
        print(f"Detalhes OK - postings: {len(details.get('posting', []))}")
