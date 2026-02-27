"""
Onboarding paso 5: Investigar keywords del nicho para Taco Madre (client_id=3).
Uso: python -m scripts.onboarding_05_research
"""
import json
import requests

CLIENT_ID = 3
URL = f"http://localhost:8000/api/seo/{CLIENT_ID}/research"

print("Investigando keywords del nicho de restaurantes... (esto tarda 10-30 seg)")

try:
    response = requests.post(URL, json={}, timeout=180)
except requests.exceptions.Timeout:
    print("ERROR: Timeout — el servidor tardó más de 60 segundos en responder.")
    raise SystemExit(1)
except requests.exceptions.ConnectionError as e:
    print(f"ERROR de conexión: {e}")
    raise SystemExit(1)

if response.ok:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    print()
    # Resumen destacado
    clusters = data.get("clusters") or data.get("clusters_generados")
    keywords = data.get("keywords_generated") or data.get("keywords_generadas")

    if clusters is not None:
        n_clusters = len(clusters) if isinstance(clusters, list) else clusters
        print(f"✓ Clusters generados: {n_clusters}")
    if keywords is not None:
        n_keywords = len(keywords) if isinstance(keywords, list) else keywords
        print(f"✓ Keywords generadas: {n_keywords}")
else:
    print(f"ERROR {response.status_code}: {response.text}")
