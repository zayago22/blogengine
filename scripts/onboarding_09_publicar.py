"""
Onboarding paso 9: Publicar artículo de Taco Madre.
Cambia POST_ID por el id obtenido en el paso 07.
Uso: python -m scripts.onboarding_09_publicar
"""
import json
import requests

POST_ID = 2  # <-- Cambia este ID por el post_id del paso 07

URL = f"http://localhost:8000/api/publish/{POST_ID}/go-live"

print("Publicando articulo...")

try:
    response = requests.post(URL, timeout=30)
except requests.exceptions.Timeout:
    print("ERROR: Timeout — el servidor tardo mas de 30 segundos.")
    raise SystemExit(1)
except requests.exceptions.ConnectionError as e:
    print(f"ERROR de conexion: {e}")
    raise SystemExit(1)

if not response.ok:
    print(f"ERROR {response.status_code}: {response.text}")
    raise SystemExit(1)

data = response.json()
print(json.dumps(data, indent=2, ensure_ascii=False))
print()

status  = data.get("status") or data.get("estado")
url     = data.get("url") or data.get("url_publicado") or data.get("blog_url")
message = data.get("message") or data.get("mensaje") or data.get("detail")

if status:
    print(f"✓ Estado: {status}")
if url:
    print(f"✓ URL: {url}")
if message:
    print(f"✓ Mensaje: {message}")

print()
print("-> Abre el blog en: http://localhost:8000/b/taco-madre")
