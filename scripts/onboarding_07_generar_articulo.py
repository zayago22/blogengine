"""
Onboarding paso 7: Generar artículo SEO-optimizado para Taco Madre (client_id=3).
Cambia KEYWORD_ID por el ID elegido en el paso 06.
Uso: python -m scripts.onboarding_07_generar_articulo
"""
import json
import requests

CLIENT_ID = 3
KEYWORD_ID = 35  # <-- Cambia este ID por el que elegiste en el paso 06

URL = f"http://localhost:8000/api/seo/{CLIENT_ID}/generate/from-keyword"

print("Generando articulo SEO-optimizado... (esto tarda 15-45 seg)")
print("Pipeline: DeepSeek escribe -> Auditoria 15 criterios -> Correccion si necesita -> Money links")
print()

try:
    response = requests.post(URL, json={"keyword_id": KEYWORD_ID}, timeout=120)
except requests.exceptions.Timeout:
    print("ERROR: Timeout — el servidor tardo mas de 120 segundos.")
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

# Resumen destacado
post_id     = data.get("post_id") or data.get("id")
titulo      = data.get("titulo") or data.get("title")
seo_score   = data.get("seo_score") or data.get("score") or data.get("puntuacion")
keyword     = data.get("keyword") or data.get("keyword_principal")
costo       = data.get("costo_usd") or data.get("costo_ia_total_usd") or data.get("cost")
money_links = data.get("money_links_injected") or data.get("money_links")
estado      = data.get("estado") or data.get("status")

if post_id is not None:
    print(f"✓ Post ID: {post_id}")
if titulo:
    print(f"✓ Titulo: {titulo}")
if seo_score is not None:
    print(f"✓ Score SEO: {seo_score}/100")
if keyword:
    print(f"✓ Keyword: {keyword}")
if costo is not None:
    print(f"✓ Costo: ${costo}")
if money_links is not None:
    print(f"✓ Money links: {money_links}")
if estado:
    print(f"✓ Estado: {estado}")

print()
if seo_score is not None:
    if seo_score >= 70:
        print("✓ LISTO PARA PUBLICAR")
    else:
        print("Score bajo, pero se puede publicar de todas formas")

print()
if post_id is not None:
    print(f"-> Usa el post_id {post_id} en el paso 09 para publicar")
