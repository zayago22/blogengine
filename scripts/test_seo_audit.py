"""Script temporal para probar OnPageSEOOptimizer."""
import sys
sys.path.insert(0, ".")
from core.seo_strategy import OnPageSEOOptimizer

html = (
    "<h1>Comprar Casa CDMX: Todo lo que Necesitas Saber</h1>"
    "<p>Si quieres comprar casa CDMX esta guia te explica paso a paso el proceso "
    "completo. Comprar casa CDMX requiere conocer los requisitos y el credito hipotecario disponible.</p>"
    "<h2>Requisitos para Comprar Casa CDMX</h2>"
    "<p>Para comprar casa CDMX necesitas credito hipotecario, el enganche y documentos basicos.</p>"
    "<h2>Credito Hipotecario al Comprar Casa CDMX</h2>"
    "<p>El credito hipotecario es la forma mas comun de financiar comprar casa CDMX en 2024.</p>"
    "<h2>Mejores Zonas para Comprar Casa CDMX</h2>"
    "<p>Existen excelentes zonas donde comprar casa CDMX segun tu presupuesto y necesidades.</p>"
    "<p>Conoce nuestro catalogo de <a href='https://raizrentable.com/propiedades'>"
    "propiedades disponibles</a> y aprende sobre "
    "<a href='/blog/credito-hipotecario'>como tramitar tu credito hipotecario</a>.</p>"
) * 5  # ~800+ palabras

result = OnPageSEOOptimizer.audit(
    titulo="Comprar Casa CDMX: Guia Completa 2024",
    meta_description="Aprende como comprar casa CDMX. Requisitos, creditos hipotecarios y "
                     "zonas recomendadas para adquirir tu primer inmueble en Ciudad de Mexico.",
    slug="comprar-casa-cdmx-guia-completa-2024",
    contenido_html=html,
    keyword_principal="comprar casa cdmx",
    keywords_secundarias=["credito hipotecario", "enganche", "zonas residenciales cdmx"],
)

print(f"\n{'='*50}")
print(f"PUNTUACION SEO: {result['puntuacion']}/100")
print(f"{'='*50}")
print(f"Palabras: {result['stats']['palabras']}")
print(f"H2s: {result['stats']['h2s']}")
print(f"Keyword density: {result['stats']['keyword_density']}%")
print(f"Links internos: {result['stats']['links_internos']}")
print(f"Links externos: {result['stats']['links_externos']}")
print(f"\nCHECKS ({len(result['checks'])}):")
for c in result["checks"]:
    icon = "✅" if c["passed"] else "❌"
    detalle = f" — {c.get('detalle','')}" if c.get("detalle") else ""
    print(f"  {icon} {c['check']}{detalle}")
if result["problemas_criticos"]:
    print(f"\nPROBLEMAS:")
    for p in result["problemas_criticos"]:
        print(f"  {p}")
if result["sugerencias"]:
    print(f"\nSUGERENCIAS:")
    for s in result["sugerencias"]:
        print(f"  💡 {s}")
