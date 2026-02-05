#!/usr/bin/env python3
"""Debug: Ver estrutura completa de um post para identificar campos."""
import json
from src.config import get_config
from src.extract import MyCreatorExtractor, TARGET_WORKSPACES

config = get_config()
extractor = MyCreatorExtractor(config)

# Pega primeiro workspace
ws = TARGET_WORKSPACES[0]
print(f"🏙️ Workspace: {ws['name']}")

# Busca lista de posts
plans = extractor.fetch_posts_list(ws["id"])
if not plans:
    print("❌ Nenhum post encontrado")
    exit(1)

print(f"📦 Posts encontrados: {len(plans)}")

# Pega detalhes do primeiro post
plan = plans[0]
plan_id = plan["_id"]
print(f"\n🔍 Analisando post: {plan_id}")

details = extractor.fetch_plan_details(plan_id, ws["id"])
if not details:
    print("❌ Não conseguiu detalhes")
    exit(1)

# Mostra estrutura
print("\n" + "=" * 60)
print("📋 CAMPOS PRINCIPAIS DO POST:")
print("=" * 60)

# Campos de nível raiz
print(f"\n🔹 type: {details.get('type')}")
print(f"🔹 status: {details.get('status')}")
print(f"🔹 created_at: {details.get('created_at')}")

# Execution time
exec_time = details.get("execution_time", {})
print(f"\n📅 execution_time.date: {exec_time.get('date')}")

# Common sharing details
common = details.get("common_sharing_details", {})
print(f"\n📝 common_sharing_details:")
print(f"   • title: {common.get('title')}")
print(f"   • message (primeiros 100 chars): {str(common.get('message', ''))[:100]}...")

# POSTING - onde está a info de plataforma!
postings = details.get("posting", [])
print(f"\n📱 posting ({len(postings)} items):")
for i, p in enumerate(postings):
    print(f"\n   [{i+1}] -------")
    print(f"   • platform_type: {p.get('platform_type')}")
    print(f"   • platform: {p.get('platform')}")
    print(f"   • platform_id: {p.get('platform_id')}")
    print(f"   • posted_id: {p.get('posted_id')}")
    print(f"   • link: {p.get('link', '')[:50]}...")
    print(f"   • post_type: {p.get('post_type')}")
    print(f"   • first_comment: {p.get('first_comment')}")
    
    # Procura por mais campos de title
    for key in ['title', 'name', 'caption', 'label']:
        if key in p:
            print(f"   • {key}: {p.get(key)}")

# Mostra todas as chaves disponíveis no posting
if postings:
    print(f"\n🔑 TODAS AS CHAVES em posting[0]:")
    for key in sorted(postings[0].keys()):
        val = postings[0][key]
        val_preview = str(val)[:80] if val else "None"
        print(f"   • {key}: {val_preview}")

# Procura campos com 'name' ou 'title' em qualquer lugar
print("\n🔍 BUSCA POR CAMPOS 'name'/'title' em todo o JSON:")
def find_fields(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if 'name' in k.lower() or 'title' in k.lower():
                print(f"   {path}.{k} = {str(v)[:80]}")
            find_fields(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_fields(item, f"{path}[{i}]")

find_fields(details)
