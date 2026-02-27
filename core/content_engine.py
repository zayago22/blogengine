"""
BlogEngine - Content Engine v2 (SEO-First).

PRINCIPIO: No generamos "artículos bonitos". Generamos máquinas de
posicionamiento en Google que llevan tráfico al negocio del cliente.

PIPELINE COMPLETO:
==================
1. INVESTIGAR → ¿Qué keywords tiene sentido atacar para este cliente?
2. PLANIFICAR  → Organizar keywords en clusters, definir calendario
3. GENERAR     → Crear artículo optimizado para UNA keyword específica
4. AUDITAR     → Verificar que cumple TODOS los criterios SEO
5. CORREGIR    → Si no pasa la auditoría, IA corrige automáticamente
6. ENLAZAR     → Inyectar money links + internal links
7. PUBLICAR    → Solo si puntuación SEO >= 70
8. INDEXAR     → Ping a Google para indexación rápida
9. MEDIR       → Trackear posición de la keyword en Google

CADA ARTÍCULO DEBE:
- Atacar UNA keyword principal con density 1-2%
- Tener keyword en título, H1, primer párrafo, meta description, slug
- Incluir 3-5 keywords secundarias
- Enlazar a 1-2 páginas de dinero del cliente (donde convierte)
- Enlazar a 2-3 artículos del mismo blog (internal linking)
- Pasar auditoría SEO con puntuación >= 70/100
"""
import logging
import json
import yaml
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from core.ai_router import get_ai_router
from core.ai_providers.base import AIResponse
from core.cost_tracker import CostTracker
from core.seo_strategy import (
    OnPageSEOOptimizer,
    SEOPromptBuilder,
    KeywordStrategyPlanner,
    MoneyPage as MoneyPageDTO,
)
from models.client import Client
from models.blog_post import BlogPost
from models.seo_strategy import MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MIN_SEO_SCORE = 70  # Puntuación mínima para publicar


@dataclass
class GenerationResult:
    """Resultado de la generación de un artículo."""
    blog_post_id: int
    titulo: str
    slug: str
    meta_description: str
    keyword_principal: str
    seo_score: int
    seo_passed: bool
    costo_total_usd: float
    tokens_total: int
    url_publicado: Optional[str] = None
    problemas_seo: list = None
    revision_count: int = 0


class ContentEngine:
    """
    Motor de generación de contenido SEO-first.
    
    USO TÍPICO:
    
    # 1. Investigar keywords para el cliente
    strategy = await engine.research_keywords(client)
    
    # 2. Generar artículo para una keyword específica
    result = await engine.generate_for_keyword(client, keyword_id=42)
    
    # 3. O generar con keyword directa
    result = await engine.generate_article(
        client=client,
        keyword="comprar casa cdmx",
        keywords_secundarias=["crédito hipotecario", "enganche"],
    )
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.router = get_ai_router()
        self.tracker = CostTracker(db)
        self.optimizer = OnPageSEOOptimizer()

    # =================================================================
    # PASO 1: INVESTIGACIÓN DE KEYWORDS
    # =================================================================

    async def research_keywords(
        self,
        client: Client,
        num_keywords: int = 20,
    ) -> dict:
        """
        Genera estrategia de keywords para un cliente usando IA.
        Crea clusters temáticos y keywords priorizadas en la BD.
        
        Returns:
            Estrategia completa con clusters y calendario.
        """
        # Obtener keywords ya usadas
        result = await self.db.execute(
            select(SEOKeyword.keyword).where(SEOKeyword.client_id == client.id)
        )
        existing = [row[0] for row in result.all()]

        # Obtener servicios desde money pages
        result = await self.db.execute(
            select(MoneyPage).where(MoneyPage.client_id == client.id, MoneyPage.activa == True)
        )
        money_pages = result.scalars().all()
        services = [mp.titulo for mp in money_pages] or [client.industria]

        # Construir prompt
        system, user = KeywordStrategyPlanner.build_strategy_prompt(
            client_name=client.nombre,
            client_industry=client.industria,
            client_services=services,
            client_location="México",  # TODO: desde config del cliente
            existing_keywords=existing,
            num_keywords=num_keywords,
        )

        # Generar con IA
        response = await self.router.generate(
            task_type="estrategia_editorial",
            client_plan=client.plan,
            prompt=user,
            system=system,
            max_tokens=4000,
            temperature=0.7,
        )

        if not response.exito:
            # Fallback: intentar con DeepSeek directamente
            response = await self.router.generate_direct(
                provider_id="deepseek",
                model="deepseek-chat",
                prompt=user,
                system=system,
                max_tokens=4000,
            )

        await self.tracker.registrar(
            client_id=client.id,
            tipo_tarea="estrategia_editorial",
            response=response,
        )

        if not response.exito:
            raise RuntimeError(f"Error investigando keywords: {response.error}")

        # Parsear JSON
        strategy = self._parse_json_response(response.contenido)
        if not strategy:
            raise RuntimeError("No se pudo parsear la estrategia de keywords")

        # Guardar en BD
        await self._save_strategy_to_db(client.id, strategy)

        return strategy

    async def _save_strategy_to_db(self, client_id: int, strategy: dict):
        """Guarda clusters y keywords en la base de datos."""
        for cluster_data in strategy.get("clusters", []):
            # Crear cluster
            cluster = TopicCluster(
                client_id=client_id,
                nombre=cluster_data.get("nombre", ""),
                pillar_keyword=cluster_data.get("pillar_keyword", ""),
                pillar_titulo_sugerido=cluster_data.get("pillar_titulo_sugerido", ""),
            )
            self.db.add(cluster)
            await self.db.flush()

            # Crear keyword del pillar
            pillar_kw = SEOKeyword(
                client_id=client_id,
                cluster_id=cluster.id,
                keyword=cluster_data.get("pillar_keyword", ""),
                titulo_sugerido=cluster_data.get("pillar_titulo_sugerido", ""),
                es_pillar=True,
                prioridad=5,
                dificultad_estimada="alta",
            )
            self.db.add(pillar_kw)

            # Crear keywords del cluster
            for kw_data in cluster_data.get("keywords", []):
                kw = SEOKeyword(
                    client_id=client_id,
                    cluster_id=cluster.id,
                    keyword=kw_data.get("keyword", ""),
                    intencion=kw_data.get("intencion", "informacional"),
                    dificultad_estimada=kw_data.get("dificultad_estimada", "media"),
                    volumen_estimado=kw_data.get("volumen_estimado", "medio"),
                    titulo_sugerido=kw_data.get("titulo_sugerido", ""),
                    prioridad=kw_data.get("prioridad", 3),
                )
                self.db.add(kw)

        await self.db.flush()

    # =================================================================
    # PASO 2: GENERACIÓN SEO-FIRST
    # =================================================================

    async def generate_for_keyword(
        self, client: Client, keyword_id: int
    ) -> GenerationResult:
        """
        Genera artículo para una keyword de la estrategia del cliente.
        Toma la keyword de la BD, genera y audita.
        """
        result = await self.db.execute(
            select(SEOKeyword).where(
                SEOKeyword.id == keyword_id,
                SEOKeyword.client_id == client.id,
            )
        )
        kw = result.scalar_one_or_none()
        if not kw:
            raise ValueError(f"Keyword #{keyword_id} no encontrada para este cliente")

        gen_result = await self.generate_article(
            client=client,
            keyword=kw.keyword,
            keywords_secundarias=kw.keywords_secundarias or [],
            titulo_sugerido=kw.titulo_sugerido,
            cluster_id=kw.cluster_id,
            is_pillar=kw.es_pillar,
        )

        # Actualizar keyword en BD
        kw.estado = "publicado" if gen_result.seo_passed else "en_progreso"
        kw.blog_post_id = gen_result.blog_post_id
        await self.db.flush()

        return gen_result

    async def generate_article(
        self,
        client: Client,
        keyword: str,
        keywords_secundarias: list[str] = None,
        titulo_sugerido: str = "",
        cluster_id: int = None,
        is_pillar: bool = False,
    ) -> GenerationResult:
        """
        Pipeline completo de generación SEO-first.
        
        1. Obtener money pages del cliente
        2. Obtener artículos existentes (para internal linking)
        3. Construir prompt SEO-optimizado
        4. Generar borrador (DeepSeek)
        5. Auditar SEO on-page
        6. Si no pasa → corregir con Claude (hasta 2 intentos)
        7. Inyectar money links + internal links
        8. Guardar resultado
        """
        keywords_sec = keywords_secundarias or []
        target_words = 1500 if is_pillar else 1000

        # --- Obtener contexto SEO del cliente ---
        money_pages = await self._get_money_pages(client.id)
        existing_posts = await self._get_existing_posts(client.id)
        
        # Seleccionar money pages más relevantes para esta keyword
        relevant_money = self._select_relevant_money_pages(keyword, money_pages)

        # --- Crear registro en BD ---
        blog_post = BlogPost(
            client_id=client.id,
            titulo=titulo_sugerido or keyword,
            slug=self._keyword_to_slug(keyword),
            keyword_principal=keyword,
            keywords_secundarias=keywords_sec,
            estado="generando",
        )
        self.db.add(blog_post)
        await self.db.flush()

        # ============================================================
        # PASO 3: GENERAR CON PROMPT SEO-FIRST
        # ============================================================
        
        seo_config = self._load_prompt_industria(client.prompt_industria or "general")
        
        system_prompt, user_prompt = SEOPromptBuilder.build_generation_prompt(
            tema=titulo_sugerido or f"Artículo sobre {keyword}",
            keyword_principal=keyword,
            keywords_secundarias=keywords_sec,
            client_name=client.nombre,
            client_industry=client.industria or "general",
            client_tone=client.tono_de_marca or "profesional",
            client_url=client.sitio_web,
            money_pages=[
                MoneyPageDTO(
                    url=mp.url,
                    titulo=mp.titulo,
                    keywords_target=mp.keywords_target or [],
                    anchor_texts=mp.anchor_texts or [mp.titulo],
                    tipo=mp.tipo,
                    prioridad=mp.prioridad,
                )
                for mp in relevant_money
            ],
            existing_posts=[
                {"titulo": p.titulo, "url": f"/{p.slug}"}
                for p in existing_posts[:5]
            ],
            language=client.idioma or "es",
            target_words=target_words,
        )

        # Agregar instrucciones de industria al system prompt
        if seo_config.get("instrucciones"):
            system_prompt += f"\n\nINSTRUCCIONES DE LA INDUSTRIA:\n{seo_config['instrucciones']}"

        logger.info(
            f"[ContentEngine] Generando para keyword '{keyword}' | "
            f"Cliente: {client.nombre} | Money pages: {len(relevant_money)}"
        )

        response = await self.router.generate(
            task_type="generacion_articulo",
            client_plan=client.plan,
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=4500 if is_pillar else 3500,
            temperature=0.7,
        )

        if not response.exito:
            blog_post.estado = "fallido"
            await self.db.flush()
            raise RuntimeError(f"Error generando artículo: {response.error}")

        await self.tracker.registrar(
            client_id=client.id,
            tipo_tarea="generacion_articulo",
            response=response,
            blog_post_id=blog_post.id,
            prompt_preview=user_prompt[:500],
        )

        costo_total = response.costo_usd
        tokens_total = response.tokens_total

        # Parsear metadata y contenido
        metadata = self._parse_metadata(response.contenido, keyword)
        contenido_html = metadata["contenido_html"]
        
        blog_post.titulo = metadata["titulo"]
        blog_post.slug = metadata["slug"]
        blog_post.meta_description = metadata["meta_description"]
        blog_post.extracto = metadata["extracto"]
        blog_post.proveedor_generacion = response.proveedor
        blog_post.modelo_generacion = response.modelo

        # ============================================================
        # PASO 4-5: AUDITAR Y CORREGIR
        # ============================================================

        revision_count = 0
        max_revisions = 2 if self.router.is_task_available("revision_editorial", client.plan) else 0

        for attempt in range(max_revisions + 1):
            # Auditar
            audit = self.optimizer.audit(
                titulo=blog_post.titulo,
                meta_description=blog_post.meta_description or "",
                slug=blog_post.slug,
                contenido_html=contenido_html,
                keyword_principal=keyword,
                keywords_secundarias=keywords_sec,
            )

            seo_score = audit["puntuacion"]
            logger.info(
                f"[ContentEngine] Auditoría SEO intento {attempt + 1}: "
                f"{seo_score}/100 | Problemas: {len(audit['problemas_criticos'])}"
            )

            # Si pasa o no hay revisiones disponibles → salir
            if seo_score >= MIN_SEO_SCORE or attempt >= max_revisions:
                break

            # Corregir con Claude
            logger.info(f"[ContentEngine] Score {seo_score} < {MIN_SEO_SCORE}, enviando a corrección...")
            
            review_prompt = SEOPromptBuilder.build_review_prompt(
                contenido_html=contenido_html,
                keyword_principal=keyword,
                keywords_secundarias=keywords_sec,
                audit_result=audit,
                client_tone=client.tono_de_marca or "profesional",
            )

            review_response = await self.router.generate(
                task_type="revision_editorial",
                client_plan=client.plan,
                prompt=review_prompt,
                system="Eres un editor SEO experto. Corrige SOLO los problemas indicados. Devuelve el HTML corregido.",
                max_tokens=4096,
                temperature=0.3,
            )

            if review_response.exito:
                contenido_html = review_response.contenido
                costo_total += review_response.costo_usd
                tokens_total += review_response.tokens_total
                revision_count += 1

                await self.tracker.registrar(
                    client_id=client.id,
                    tipo_tarea="revision_editorial",
                    response=review_response,
                    blog_post_id=blog_post.id,
                )

                blog_post.proveedor_revision = review_response.proveedor
                blog_post.modelo_revision = review_response.modelo

        # Auditoría final
        final_audit = self.optimizer.audit(
            titulo=blog_post.titulo,
            meta_description=blog_post.meta_description or "",
            slug=blog_post.slug,
            contenido_html=contenido_html,
            keyword_principal=keyword,
            keywords_secundarias=keywords_sec,
        )
        seo_score = final_audit["puntuacion"]
        seo_passed = seo_score >= MIN_SEO_SCORE

        # Guardar auditoría en BD
        audit_log = SEOAuditLog(
            blog_post_id=blog_post.id,
            client_id=client.id,
            puntuacion=seo_score,
            keyword_principal=keyword,
            checks=final_audit["checks"],
            problemas_criticos=final_audit["problemas_criticos"],
            sugerencias=final_audit["sugerencias"],
            stats=final_audit["stats"],
            aprobado=seo_passed,
            revision_automatica=revision_count > 0,
        )
        self.db.add(audit_log)

        # ============================================================
        # PASO 6: INYECTAR MONEY LINKS + INTERNAL LINKS
        # ============================================================
        contenido_html = self._ensure_money_links(contenido_html, relevant_money)
        contenido_html = self._ensure_internal_links(contenido_html, existing_posts, keyword)

        # ============================================================
        # GUARDAR RESULTADO
        # ============================================================
        blog_post.contenido_html = contenido_html
        blog_post.costo_ia_total_usd = costo_total
        blog_post.tokens_input_total = tokens_total

        if seo_passed:
            blog_post.estado = "aprobado" if client.auto_publish else "en_revision"
        else:
            blog_post.estado = "en_revision"
            logger.warning(
                f"[ContentEngine] Artículo NO pasó auditoría SEO ({seo_score}/100). "
                f"Requiere revisión manual."
            )

        await self.db.flush()
        await self.db.refresh(blog_post)

        logger.info(
            f"[ContentEngine] ✅ Artículo generado: '{blog_post.titulo}' | "
            f"SEO: {seo_score}/100 | Costo: ${costo_total:.4f} | "
            f"Revisiones: {revision_count}"
        )

        return GenerationResult(
            blog_post_id=blog_post.id,
            titulo=blog_post.titulo,
            slug=blog_post.slug,
            meta_description=blog_post.meta_description or "",
            keyword_principal=keyword,
            seo_score=seo_score,
            seo_passed=seo_passed,
            costo_total_usd=costo_total,
            tokens_total=tokens_total,
            problemas_seo=final_audit["problemas_criticos"],
            revision_count=revision_count,
        )

    # =================================================================
    # PASO 7: SOCIAL COPIES (subordinado al SEO)
    # =================================================================

    async def generate_social_copies(
        self,
        client: Client,
        blog_post: BlogPost,
        redes: list[str],
    ) -> dict[str, str]:
        """
        Genera copies para redes sociales.
        El objetivo: distribuir el artículo para generar backlinks sociales
        y tráfico que refuerce la señal de autoridad para Google.
        """
        copies = {}
        url_articulo = blog_post.url_publicado or f"/{blog_post.slug}"

        for red in redes:
            prompt = self._build_social_prompt(
                red, blog_post, client, url_articulo
            )

            response = await self.router.generate(
                task_type="copies_redes_sociales",
                client_plan=client.plan,
                prompt=prompt,
                system=f"Genera contenido para {red}. El objetivo es llevar tráfico al artículo.",
                max_tokens=1000,
                temperature=0.8,
            )

            if response.exito:
                copies[red] = response.contenido
                await self.tracker.registrar(
                    client_id=client.id,
                    tipo_tarea="copies_redes_sociales",
                    response=response,
                )

        return copies

    # =================================================================
    # HELPERS PRIVADOS
    # =================================================================

    async def _get_money_pages(self, client_id: int) -> list[MoneyPage]:
        """Obtiene las money pages activas del cliente."""
        result = await self.db.execute(
            select(MoneyPage)
            .where(MoneyPage.client_id == client_id, MoneyPage.activa == True)
            .order_by(MoneyPage.prioridad.desc())
        )
        return list(result.scalars().all())

    async def _get_existing_posts(self, client_id: int) -> list[BlogPost]:
        """Obtiene posts publicados del cliente para internal linking."""
        result = await self.db.execute(
            select(BlogPost)
            .where(BlogPost.client_id == client_id, BlogPost.estado == "publicado")
            .order_by(desc(BlogPost.fecha_publicado))
            .limit(20)
        )
        return list(result.scalars().all())

    def _select_relevant_money_pages(
        self, keyword: str, money_pages: list[MoneyPage], max_pages: int = 2
    ) -> list[MoneyPage]:
        """
        Selecciona las money pages más relevantes para una keyword.
        Prioriza por: coincidencia de keywords > prioridad.
        """
        keyword_lower = keyword.lower()
        scored = []
        
        for mp in money_pages:
            score = mp.prioridad
            # Bonus si la keyword del artículo coincide con las keywords de la money page
            mp_keywords = [k.lower() for k in (mp.keywords_target or [])]
            for mk in mp_keywords:
                if mk in keyword_lower or keyword_lower in mk:
                    score += 10
                elif any(word in keyword_lower for word in mk.split()):
                    score += 3
            scored.append((score, mp))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mp for _, mp in scored[:max_pages]]

    def _ensure_money_links(
        self, html: str, money_pages: list[MoneyPage]
    ) -> str:
        """
        Verifica que el artículo tenga links a las money pages.
        Si no los tiene, los inyecta en el CTA o al final.
        """
        for mp in money_pages:
            # Verificar si ya tiene link a esta URL
            if mp.url in html:
                continue
            
            # Intentar insertar antes del último </p>
            anchors = mp.anchor_texts or [mp.titulo]
            anchor = anchors[0]
            link_html = f'<a href="{mp.url}" title="{mp.titulo}">{anchor}</a>'
            
            # Buscar un lugar natural para insertarlo
            # Intentar en el último párrafo antes del cierre
            last_p = html.rfind("</p>")
            if last_p > 0:
                insert_text = f' Si te interesa, puedes conocer más sobre {link_html}.'
                html = html[:last_p] + insert_text + html[last_p:]

        return html

    def _ensure_internal_links(
        self, html: str, existing_posts: list[BlogPost], current_keyword: str
    ) -> str:
        """
        Verifica que haya internal links. Si no, inyecta links
        a artículos relevantes del mismo blog.
        """
        # Contar links internos existentes
        link_count = len(re.findall(r'<a[^>]+href=["\']/[^"\']*["\']', html))
        if link_count >= 2:
            return html  # Ya tiene suficientes
        
        # Buscar posts relacionados por keyword
        for post in existing_posts:
            if link_count >= 3:
                break
            post_keyword = (post.keyword_principal or "").lower()
            if post_keyword and (
                post_keyword in current_keyword.lower()
                or current_keyword.lower() in post_keyword
                or any(w in current_keyword.lower() for w in post_keyword.split() if len(w) > 3)
            ):
                link = f'<a href="/{post.slug}" title="{post.titulo}">{post.titulo}</a>'
                if post.slug not in html:
                    # Insertar como "artículo relacionado" antes del CTA
                    insert = f'<p>Te puede interesar: {link}</p>'
                    cta_pos = html.find('class="cta-box"')
                    if cta_pos > 0:
                        p_before = html.rfind("<div", 0, cta_pos)
                        if p_before > 0:
                            html = html[:p_before] + insert + "\n" + html[p_before:]
                    else:
                        last_p = html.rfind("</p>")
                        if last_p > 0:
                            html = html[:last_p + 4] + "\n" + insert + html[last_p + 4:]
                    link_count += 1

        return html

    def _keyword_to_slug(self, keyword: str) -> str:
        """Convierte keyword a slug URL-friendly."""
        slug = keyword.lower().strip()
        slug = re.sub(r'[áàäâ]', 'a', slug)
        slug = re.sub(r'[éèëê]', 'e', slug)
        slug = re.sub(r'[íìïî]', 'i', slug)
        slug = re.sub(r'[óòöô]', 'o', slug)
        slug = re.sub(r'[úùüû]', 'u', slug)
        slug = re.sub(r'[ñ]', 'n', slug)
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')

    def _parse_metadata(self, contenido: str, keyword: str) -> dict:
        """Extrae metadata SEO del contenido generado."""
        lineas = contenido.strip().split("\n")
        titulo = keyword.title()
        slug = self._keyword_to_slug(keyword)
        meta_description = ""
        extracto = ""
        contenido_html = contenido

        for linea in lineas:
            ls = linea.strip()
            if ls.startswith("META_TITLE:"):
                titulo = ls.replace("META_TITLE:", "").strip()
            elif ls.startswith("META_DESCRIPTION:"):
                meta_description = ls.replace("META_DESCRIPTION:", "").strip()
            elif ls.startswith("SLUG:"):
                slug = ls.replace("SLUG:", "").strip()
            elif ls.startswith("EXTRACTO:"):
                extracto = ls.replace("EXTRACTO:", "").strip()

        # Limpiar metadata del HTML
        for prefix in ["META_TITLE:", "META_DESCRIPTION:", "SLUG:", "EXTRACTO:"]:
            for linea in lineas:
                if linea.strip().startswith(prefix):
                    contenido_html = contenido_html.replace(linea, "").strip()

        return {
            "titulo": titulo,
            "slug": slug or self._keyword_to_slug(keyword),
            "meta_description": meta_description,
            "extracto": extracto,
            "contenido_html": contenido_html,
        }

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Parsea respuesta JSON de la IA (con tolerancia a formato)."""
        # Limpiar backticks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Intentar encontrar JSON dentro del texto
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _load_prompt_industria(self, industria: str) -> dict:
        """Carga prompts por industria."""
        archivo = PROMPTS_DIR / f"{industria}.yaml"
        if not archivo.exists():
            archivo = PROMPTS_DIR / "general.yaml"
        if archivo.exists():
            with open(archivo, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _build_social_prompt(
        self, red: str, post: BlogPost, client: Client, url: str
    ) -> str:
        """Prompt para copies de redes sociales."""
        base = f"""Genera un post para {red.upper()} que lleve tráfico a este artículo:

TÍTULO: {post.titulo}
URL: {url}
EXTRACTO: {post.extracto or ''}
KEYWORD: {post.keyword_principal or ''}
NEGOCIO: {client.nombre}
TONO: {client.tono_de_marca}
SITIO WEB: {client.sitio_web}

OBJETIVO: Que la gente haga clic y lea el artículo completo.
"""
        specs = {
            "facebook": "Post de 100-200 palabras. Hook fuerte. CTA para leer. 3-5 hashtags.",
            "instagram": "Caption de 150-300 palabras. Hook → tips del artículo → CTA 'link en bio'. 20-25 hashtags.\nAdemás genera texto para CARRUSEL de 5-7 slides.",
            "linkedin": "Post profesional 150-250 palabras. Dato o reflexión impactante. Pregunta al final. 3-5 hashtags.",
            "twitter": "Hilo de 3-5 tweets (cada uno máx 280 chars). Gancho → puntos clave → CTA con link.",
            "pinterest": "Descripción SEO de 150-300 chars. Rica en keywords.",
            "google_business": "Post breve, máx 300 palabras. Valor principal del artículo + CTA local.",
        }
        return base + specs.get(red, "Post apropiado para la red.")
