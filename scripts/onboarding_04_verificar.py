"""
Onboarding paso 4: Verificar cliente y money pages de Taco Madre.
Uso: python -m scripts.onboarding_04_verificar
"""
import json
import requests

CLIENT_ID = 3
BASE_URL = "http://localhost:8000"

# 1. GET cliente
print("=== CLIENTE ===")
r = requests.get(f"{BASE_URL}/api/clients/{CLIENT_ID}")
if r.ok:
    cliente = r.json()
    print(json.dumps(cliente, indent=2, ensure_ascii=False))
else:
    print(f"ERROR {r.status_code}: {r.text}")
    cliente = None

print()

# 2. GET money pages
print("=== MONEY PAGES ===")
r2 = requests.get(f"{BASE_URL}/api/seo/{CLIENT_ID}/money-pages")
if r2.ok:
    money_pages = r2.json()
    print(json.dumps(money_pages, indent=2, ensure_ascii=False))
else:
    print(f"ERROR {r2.status_code}: {r2.text}")
    money_pages = []

print()

# Resumen
if cliente:
    print(f"✓ Cliente: {cliente.get('nombre')} ({cliente.get('industria')})")
    print(f"✓ Blog slug: {cliente.get('blog_slug')}")
    cantidad = len(money_pages) if isinstance(money_pages, list) else 0
    print(f"✓ Money pages: {cantidad}")
