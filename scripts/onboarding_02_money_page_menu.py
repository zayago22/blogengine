"""
Onboarding paso 2: Registrar money page (menú) para Taco Madre (client_id=3).
Uso: python -m scripts.onboarding_02_money_page_menu
"""
import json
import requests

CLIENT_ID = 3
URL = f"http://localhost:8000/api/seo/{CLIENT_ID}/money-pages"

payload = {
    "url": "https://tacomadre.com/menu",
    "titulo": "Nuestro Menú",
    "tipo": "servicio",
    "anchor_texts": ["ver menú", "nuestros platillos", "carta completa"],
    "prioridad": 1,
}

response = requests.post(URL, json=payload)

if response.ok:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"ERROR {response.status_code}: {response.text}")
