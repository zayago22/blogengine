"""
Onboarding paso 8: Ver posts generados para Taco Madre (client_id=3).
Uso: python -m scripts.onboarding_08_ver_post
"""
import re
import requests

CLIENT_ID = 3
BASE_URL = "http://localhost:8000"


def strip_html(html: str) -> str:
    """Quita tags HTML y colapsa espacios."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# 1. GET cliente para obtener blog_slug
r = requests.get(f"{BASE_URL}/api/clients/{CLIENT_ID}", timeout=10)
if not r.ok:
    print(f"ERROR obteniendo cliente: {r.status_code} {r.text}")
    raise SystemExit(1)
cliente = r.json()
blog_slug = cliente.get("blog_slug", "")

# 2. Listar posts del cliente
r2 = requests.get(f"{BASE_URL}/api/posts/", params={"client_id": CLIENT_ID}, timeout=10)
if not r2.ok:
    print(f"ERROR listando posts: {r2.status_code} {r2.text}")
    raise SystemExit(1)

posts = r2.json()
if not posts:
    print("No hay posts para este cliente.")
    print("Asegurate de haber ejecutado el paso 07 (generar articulo).")
    raise SystemExit(0)

for post in posts:
    post_id = post.get("id")

    # GET detalle del post para obtener contenido_html
    r3 = requests.get(f"{BASE_URL}/api/posts/{post_id}", timeout=10)
    detail = r3.json() if r3.ok else post

    print("=== POST ===")
    print(f"ID: {post_id}")
    print(f"Titulo: {detail.get('titulo', '-')}")
    print(f"Keyword: {detail.get('keyword_principal', '-')}")
    print(f"Score SEO: {detail.get('seo_score') or detail.get('puntuacion') or '-'}/100")
    print(f"Estado: {detail.get('estado', '-')}")
    print(f"Slug: {detail.get('slug', '-')}")

    contenido_html = detail.get("contenido_html") or ""
    if contenido_html:
        texto = strip_html(contenido_html)[:500]
        print(f"\nExtracto del contenido:\n{texto}...")

    print()
    print(f"-> Para ver el post completo abre: {BASE_URL}/admin/posts/{post_id}/")
    print(f"-> Blog publico: {BASE_URL}/b/{blog_slug}/{detail.get('slug', '')}")
    print()

print("-> Para publicar, pasa al paso 09")
