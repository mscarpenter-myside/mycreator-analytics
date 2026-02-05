"""
Script para inspecionar a estrutura REAL de um post e achar o ID Externo.
Rode com: python -m src.inspect_post
"""
import json
import logging
from src.config import get_config
from src.extract import MyCreatorExtractor

# Configura logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inspector")

def inspect():
    config = get_config()
    extractor = MyCreatorExtractor(config)
    
    # Busca os posts
    print("📡 Buscando posts...")
    posts = extractor.fetch_posts_list()
    
    if not posts:
        print("❌ Nenhum post encontrado para inspecionar.")
        return

    # Pega o primeiro post da lista
    post = posts[0]
    
    # Salva em um arquivo para facilitar a leitura
    filename = "debug_post_structure.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(post, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ Estrutura do post salva em: {filename}")
    print("-" * 50)
    print("🔎 PROCURANDO POR IDs CANDIDATOS:")
    
    # Varredura simples para mostrar tudo que parece um ID
    def find_ids(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                find_ids(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                find_ids(item, f"{path}[{i}]")
        elif isinstance(obj, (str, int)):
            # Se parece um ID longo (Instagram tem ~17-19 dígitos)
            s_val = str(obj)
            if s_val.isdigit() and len(s_val) > 10:
                print(f"   👉 {path}: {s_val}")

    find_ids(post)
    print("-" * 50)
    print("Abra o arquivo 'debug_post_structure.json' se precisar ver tudo.")

if __name__ == "__main__":
    inspect()