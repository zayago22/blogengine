"""
Onboarding paso 10: Verificar el blog público de Taco Madre.
Uso: python -m scripts.onboarding_10_ver_blog
"""
import json
import requests

BASE_URL = "http://localhost:8000"
BLOG_SLUG = "taco-madre"

# 1. Blog home
print("=== BLOG HOME ===")
r = requests.get(f"{BASE_URL}/b/{BLOG_SLUG}", timeout=10)
if r.status_code == 200:
    # Check if it contains some content markers
    html = r.text
    tiene_contenido = len(html) > 500
    print(f"✓ Blog home: OK (status 200, {len(html)} bytes)")
    if not tiene_contenido:
        print("  Aviso: la respuesta parece muy corta, verifica en el navegador")
else:
    print(f"✗ Blog home: Error {r.status_code}")

print()

# 2. Posts públicos via API
print("=== POSTS PUBLICOS ===")
r2 = requests.get(f"{BASE_URL}/api/public/{BLOG_SLUG}/posts", timeout=10)
if r2.ok:
    posts = r2.json()
    if isinstance(posts, list):
        print(json.dumps(posts, indent=2, ensure_ascii=False))
        print()
        for post in posts:
            titulo = post.get("titulo") or post.get("title") or "(sin titulo)"
            slug   = post.get("slug", "")
            print(f"  - {titulo} ({slug})")
    else:
        print(json.dumps(posts, indent=2, ensure_ascii=False))
else:
    print(f"✗ API posts publicos: Error {r2.status_code} — {r2.text[:200]}")

print()

# 3. Sitemap
print("=== SITEMAP ===")
r3 = requests.get(f"{BASE_URL}/b/{BLOG_SLUG}/sitemap.xml", timeout=10)
if r3.status_code == 200:
    content_type = r3.headers.get("content-type", "")
    print(f"✓ Sitemap: OK (status 200, content-type: {content_type})")
    # Show first 300 chars of sitemap
    print(r3.text[:300])
else:
    print(f"✗ Sitemap: Error {r3.status_code}")

print()
print("================================")
print(f"Blog publico: {BASE_URL}/b/{BLOG_SLUG}")
print(f"Sitemap:      {BASE_URL}/b/{BLOG_SLUG}/sitemap.xml")
print("================================")
print("-> Abre estas URLs en tu navegador para verlo")
