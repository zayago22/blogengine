"""Script para insertar un post de prueba para ETAPA 3."""
import asyncio, sys
sys.path.insert(0, ".")
from models.base import async_session
from models.blog_post import BlogPost

HTML = (
    "<h1>Comprar Casa CDMX: Guia Completa 2024</h1>"
    "<p>Guia para comprar casa CDMX en 2024. Comprar casa CDMX requiere conocer el credito hipotecario disponible.</p>"
    "<h2>Requisitos para Comprar Casa CDMX</h2>"
    "<p>Para comprar casa CDMX necesitas credito hipotecario, enganche y documentos basicos.</p>"
    "<h2>Credito Hipotecario para Comprar Casa CDMX</h2>"
    "<p>El credito hipotecario facilita comprar casa CDMX con enganche bajo en 2024.</p>"
    "<h2>Mejores Zonas para Comprar Casa CDMX</h2>"
    "<p>Existen excelentes zonas donde comprar casa CDMX segun presupuesto.</p>"
    "<p>Visita <a href='https://raizrentable.com/propiedades'>nuestras propiedades disponibles</a> "
    "y aprende sobre <a href='/blog/credito-hipotecario'>como tramitar tu credito hipotecario</a>.</p>"
)

async def main():
    async with async_session() as db:
        post = BlogPost(
            client_id=1,
            titulo="Comprar Casa CDMX: Guia Completa 2024",
            slug="comprar-casa-cdmx-guia-completa-2024",
            keyword_principal="comprar casa cdmx",
            keywords_secundarias=["credito hipotecario", "enganche", "zonas cdmx"],
            meta_description=(
                "Aprende como comprar casa CDMX. Requisitos, creditos hipotecarios "
                "y zonas recomendadas para adquirir tu inmueble en Ciudad de Mexico."
            ),
            contenido_html=HTML,
            estado="borrador",
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        print(f"Post de prueba creado: id={post.id} | slug={post.slug}")


if __name__ == "__main__":
    asyncio.run(main())
