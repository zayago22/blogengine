"""
Onboarding paso 1: Crear cliente Taco Madre via API.
Uso: python -m scripts.onboarding_01_crear_cliente
"""
import json
import requests

URL = "http://localhost:8000/api/clients/"

payload = {
    "nombre": "Taco Madre",
    "email": "hola@tacomadre.com",
    "industria": "restaurantes",
    "sitio_web": "https://tacomadre.com",
}

response = requests.post(URL, json=payload)

if response.ok:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\nANOTA ESTE ID: {data['id']}")
else:
    print(f"ERROR {response.status_code}: {response.text}")
