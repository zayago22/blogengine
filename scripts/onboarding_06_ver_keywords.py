"""
Onboarding paso 6: Ver keywords generadas para Taco Madre (client_id=3).
Uso: python -m scripts.onboarding_06_ver_keywords
"""
import requests

CLIENT_ID = 3
URL = f"http://localhost:8000/api/seo/{CLIENT_ID}/keywords"

response = requests.get(URL, timeout=15)

if not response.ok:
    print(f"ERROR {response.status_code}: {response.text}")
    raise SystemExit(1)

keywords = response.json()

if not keywords:
    print("No hay keywords. Repite el paso 05 (research).")
    raise SystemExit(0)

# Column widths
W_ID   = 4
W_KW   = 40
W_VOL  = 9
W_DIFF = 12
W_PRIO = 11
W_EST  = 12

header = (
    f"{'ID':<{W_ID}} | "
    f"{'Keyword':<{W_KW}} | "
    f"{'Volumen':>{W_VOL}} | "
    f"{'Dificultad':<{W_DIFF}} | "
    f"{'Prioridad':>{W_PRIO}} | "
    f"{'Estado':<{W_EST}}"
)
sep = "-" * len(header)

print(header)
print(sep)

for kw in keywords:
    kid      = str(kw.get("id", "")).ljust(W_ID)
    keyword  = str(kw.get("keyword", ""))[:W_KW].ljust(W_KW)
    volume   = str(kw.get("search_volume") or kw.get("volumen") or "-").rjust(W_VOL)
    diff     = str(kw.get("difficulty") or kw.get("dificultad") or "-").ljust(W_DIFF)
    prio     = str(kw.get("priority") or kw.get("prioridad") or "-").rjust(W_PRIO)
    estado   = str(kw.get("estado") or kw.get("status") or "-").ljust(W_EST)

    print(f"{kid} | {keyword} | {volume} | {diff} | {prio} | {estado}")

print(sep)
print(f"Total: {len(keywords)} keywords")
print(f"-> Usa el ID de la keyword que mas te guste en el paso 07")
