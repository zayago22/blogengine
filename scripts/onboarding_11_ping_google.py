"""
Onboarding paso 11: Notificar a Google y Bing del nuevo artículo.
Uso: python -m scripts.onboarding_11_ping_google
"""
import json
import requests

CLIENT_ID = 3
URL = f"http://localhost:8000/api/seo/{CLIENT_ID}/ping-google"

print("Notificando a Google y Bing...")

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

google  = data.get("google")
bing    = data.get("bing")
sitemap = data.get("sitemap_url") or data.get("sitemap")

if google is not None:
    print(f"✓ Google: {google}")
if bing is not None:
    print(f"✓ Bing: {bing}")
if sitemap:
    print(f"✓ Sitemap: {sitemap}")

print()
print("================================")
print("ONBOARDING COMPLETO")
print("================================")
print("Cliente: Taco Madre")
print("Blog: http://localhost:8000/b/taco-madre")
print()
print("Resumen de lo que hiciste:")
print("1. ✓ Cliente creado")
print("2. ✓ Money pages registradas (menu + contacto)")
print("3. ✓ Keywords investigadas por IA")
print("4. ✓ Articulo generado con SEO score")
print("5. ✓ Articulo publicado")
print("6. ✓ Blog visible en la web")
print("7. ✓ Google y Bing notificados")
print()
print("Siguiente:")
print("- Genera mas articulos repitiendo pasos 07-09 con otras keywords")
print("- Crea otro cliente repitiendo desde el paso 01")
print("- Con Celery activo, todo esto se automatiza")
