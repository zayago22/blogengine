"""
BlogEngine - Seed de datos de prueba.
Crea un cliente de prueba (Raíz Rentable) con money pages.

Ejecutar: python -m scripts.seed_test_data
"""
import asyncio
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import init_db, async_session
from models.client import Client
from models.seo_strategy import MoneyPage
from sqlalchemy import select


async def seed():
    """Crea datos de prueba."""
    await init_db()

    async with async_session() as db:
        # Verificar si ya existe
        result = await db.execute(
            select(Client).where(Client.blog_slug == "raiz-rentable")
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Cliente ya existe: {existing.nombre} (id={existing.id})")
            return

        # --- Cliente de prueba ---
        client = Client(
            nombre="Raíz Rentable",
            email="contacto@raizrentable.com",
            industria="inmobiliario",
            sitio_web="https://raizrentable.com",
            tono_de_marca="profesional",
            palabras_clave_nicho=[
                "comprar casa cdmx",
                "inversión inmobiliaria",
                "crédito hipotecario",
            ],
            audiencia_objetivo="Personas de 28-55 años interesadas en comprar, vender o invertir en bienes raíces en México",
            idioma="es",
            descripcion_negocio="Raíz Rentable es una inmobiliaria digital que ayuda a personas a comprar, vender e invertir en propiedades en la Ciudad de México y zona metropolitana.",
            plan="starter",
            estado="activo",
            blog_slug="raiz-rentable",
            blog_design={
                "primary": "#1a5632",
                "background": "#ffffff",
                "text": "#1f2937",
                "accent": "#2d8a4e",
                "font": "'Inter', sans-serif",
                "logo_url": "",
            },
            blog_cta_text="Ver propiedades disponibles",
            blog_cta_url="https://raizrentable.com/propiedades",
            seo_integration_level="external",
            seo_canonical_domain="raizrentable.com",
            seo_blog_base_url="https://blogengine.app/b/raiz-rentable",
            seo_default_author="Equipo Raíz Rentable",
            frecuencia_publicacion="semanal",
            prompt_industria="inmobiliario",
        )
        db.add(client)
        await db.flush()
        await db.refresh(client)
        print(f"Cliente creado: {client.nombre} (id={client.id})")

        # --- Money Pages ---
        money_pages = [
            MoneyPage(
                client_id=client.id,
                url="https://raizrentable.com/propiedades",
                titulo="Propiedades disponibles",
                tipo="servicio",
                keywords_target=["comprar casa cdmx", "departamentos en venta"],
                anchor_texts=[
                    "Ver propiedades disponibles",
                    "Conoce nuestras propiedades",
                    "Buscar casa o departamento",
                ],
                prioridad=5,
            ),
            MoneyPage(
                client_id=client.id,
                url="https://raizrentable.com/contacto",
                titulo="Contacto - Agenda una cita",
                tipo="contacto",
                keywords_target=["asesor inmobiliario", "consulta inmobiliaria"],
                anchor_texts=[
                    "Agenda una cita con un asesor",
                    "Contacta a un experto",
                    "Solicita una asesoría gratuita",
                ],
                prioridad=4,
            ),
            MoneyPage(
                client_id=client.id,
                url="https://wa.me/5215512345678",
                titulo="WhatsApp - Contacto rápido",
                tipo="whatsapp",
                keywords_target=[],
                anchor_texts=[
                    "Escríbenos por WhatsApp",
                    "Contáctanos por WhatsApp",
                ],
                prioridad=3,
            ),
        ]

        for mp in money_pages:
            db.add(mp)
        await db.commit()

        print(f"Money pages creadas: {len(money_pages)}")
        print()
        print("Seed completado:")
        print(f"  Cliente: {client.nombre}")
        print(f"  Blog:    https://blogengine.app/b/{client.blog_slug}")
        print(f"  Plan:    {client.plan}")
        print(f"  Money pages: {len(money_pages)}")


if __name__ == "__main__":
    asyncio.run(seed())
