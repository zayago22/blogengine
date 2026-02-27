"""
Onboarding paso 3: Registrar money page (contacto) para Taco Madre (client_id=3).
Uso: python -m scripts.onboarding_03_money_page_contacto
"""
import json
import requests

CLIENT_ID = 3
URL = f"http://localhost:8000/api/seo/{CLIENT_ID}/money-pages"

payload = {
    "url": "https://tacomadre.com/contacto",
    "titulo": "Reserva tu mesa",
    "tipo": "contacto",
    "anchor_texts": ["reservar mesa", "haz tu reservación", "contáctanos"],
    "prioridad": 2,
}

response = requests.post(URL, json=payload)

if response.ok:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"ERROR {response.status_code}: {response.text}")
