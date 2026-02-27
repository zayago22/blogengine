/**
 * BlogEngine Cloudflare Worker.
 * 
 * PROXY TRANSPARENTE: Intercepta /blog/* en el dominio del cliente
 * y sirve el contenido de BlogEngine. Google ve cliente.com/blog.
 * 
 * FUNCIONA CON CUALQUIER SITIO QUE USE CLOUDFLARE.
 * No importa si el sitio es HTML, WordPress, Wix, o lo que sea.
 * Solo necesitas acceso al dashboard de Cloudflare del dominio.
 * 
 * INSTALACIÓN:
 * 1. Ir a Cloudflare → Workers & Pages → Create Worker
 * 2. Pegar este código
 * 3. Agregar route: cliente.com/blog/* → worker
 * 4. Configurar variables de entorno:
 *    - BLOGENGINE_SLUG: slug del blog (ej: "raiz-rentable")
 *    - BLOGENGINE_API_URL: https://blogengine.app (o tu dominio)
 * 
 * CÓMO FUNCIONA:
 * Visitante → cliente.com/blog/articulo
 *    ↓
 * Cloudflare Worker intercepta la request
 *    ↓
 * Worker llama a blogengine.app/api/public/slug/posts/articulo
 *    ↓
 * Worker renderiza HTML con canonical → cliente.com/blog/articulo
 *    ↓
 * Visitante (y Google) ven HTML completo con SEO del dominio del cliente ✅
 * 
 * SEO: ⭐⭐⭐⭐⭐ — Google ve el dominio del cliente, canonical correcto, schema markup.
 */

const BLOG_PATH = '/blog';

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const slug = env.BLOGENGINE_SLUG || 'default';
        const apiUrl = env.BLOGENGINE_API_URL || 'https://blogengine.app';
        const domain = url.hostname;
        const siteName = env.SITE_NAME || domain;
        const path = url.pathname;

        // /blog → index
        if (path === BLOG_PATH || path === BLOG_PATH + '/') {
            return handleIndex(apiUrl, slug, domain, siteName);
        }

        // /blog/sitemap.xml
        if (path === BLOG_PATH + '/sitemap.xml') {
            return handleSitemap(apiUrl, slug, domain);
        }

        // /blog/rss.xml
        if (path === BLOG_PATH + '/rss.xml') {
            return handleRSS(apiUrl, slug, domain, siteName);
        }

        // /blog/slug-del-post
        const postSlug = path.replace(BLOG_PATH + '/', '').replace(/\/$/, '');
        if (postSlug && !postSlug.includes('/')) {
            return handlePost(apiUrl, slug, postSlug, domain, siteName);
        }

        return new Response('Not Found', { status: 404 });
    }
};


async function handleIndex(apiUrl, slug, domain, siteName) {
    const posts = await apiFetch(apiUrl, `/api/public/${slug}/posts?limit=20`);
    if (!posts) return errorResponse();

    let cards = '';
    for (const p of posts) {
        const fecha = (p.fecha_publicado || '').substring(0, 10);
        cards += `
        <article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">
            <h2 style="margin-bottom:0.5rem;">
                <a href="${BLOG_PATH}/${p.slug}" style="color:inherit;text-decoration:none;">${esc(p.titulo)}</a>
            </h2>
            <div style="color:#888;font-size:0.875rem;margin-bottom:0.75rem;">${fecha}</div>
            <p>${esc(p.extracto || '')}</p>
            <a href="${BLOG_PATH}/${p.slug}" style="color:#2563eb;font-weight:500;">Leer más →</a>
        </article>`;
    }

    const html = layout({
        title: `Blog | ${siteName}`,
        description: `Blog de ${siteName}`,
        canonical: `https://${domain}${BLOG_PATH}/`,
        domain, siteName,
        content: `<h1 style="font-size:2rem;margin-bottom:2rem;">Blog</h1>${cards || '<p style="text-align:center;color:#999;padding:4rem 0;">Próximamente.</p>'}`,
    });

    return new Response(html, {
        headers: {
            'Content-Type': 'text/html;charset=UTF-8',
            'Cache-Control': 'public, max-age=3600',
        },
    });
}


async function handlePost(apiUrl, slug, postSlug, domain, siteName) {
    const post = await apiFetch(apiUrl, `/api/public/${slug}/posts/${postSlug}`);
    if (!post) return new Response('Artículo no encontrado', { status: 404 });

    const canonical = `https://${domain}${BLOG_PATH}/${postSlug}`;
    const fecha = (post.fecha_publicado || '').substring(0, 10);

    const schema = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.titulo,
        "description": post.meta_description || '',
        "url": canonical,
        "datePublished": post.fecha_publicado || '',
        "publisher": { "@type": "Organization", "name": siteName, "url": `https://${domain}` },
    });

    const breadcrumb = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "Inicio", "item": `https://${domain}` },
            { "@type": "ListItem", "position": 2, "name": "Blog", "item": `https://${domain}${BLOG_PATH}/` },
            { "@type": "ListItem", "position": 3, "name": post.titulo, "item": canonical },
        ]
    });

    const extraHead = `
    <meta name="keywords" content="${esc(post.keyword || '')}">
    ${post.imagen_destacada_url ? `<meta property="og:image" content="${post.imagen_destacada_url}">` : ''}
    <meta property="article:published_time" content="${post.fecha_publicado || ''}">
    <script type="application/ld+json">${schema}</script>
    <script type="application/ld+json">${breadcrumb}</script>`;

    const content = `
    <article>
        <h1 style="font-size:2.25rem;line-height:1.3;margin-bottom:1rem;">${esc(post.titulo)}</h1>
        <div style="color:#6b7280;margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid #f3f4f6;">${fecha}</div>
        <div style="line-height:1.8;">${post.contenido_html || ''}</div>
        <div style="margin-top:2rem;"><a href="${BLOG_PATH}/" style="color:#2563eb;text-decoration:none;">← Volver al blog</a></div>
    </article>`;

    const html = layout({
        title: `${post.titulo} | ${siteName}`,
        description: post.meta_description || '',
        canonical, domain, siteName, content, extraHead,
    });

    return new Response(html, {
        headers: {
            'Content-Type': 'text/html;charset=UTF-8',
            'Cache-Control': 'public, max-age=3600',
        },
    });
}


async function handleSitemap(apiUrl, slug, domain) {
    const posts = await apiFetch(apiUrl, `/api/public/${slug}/posts?limit=100`);
    const base = `https://${domain}${BLOG_PATH}`;
    let xml = '<?xml version="1.0" encoding="UTF-8"?>';
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
    xml += `<url><loc>${base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>`;
    for (const p of (posts || [])) {
        const d = (p.fecha_publicado || '').substring(0, 10);
        xml += `<url><loc>${base}/${p.slug}</loc><lastmod>${d}</lastmod><priority>0.8</priority></url>`;
    }
    xml += '</urlset>';
    return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}


async function handleRSS(apiUrl, slug, domain, siteName) {
    const posts = await apiFetch(apiUrl, `/api/public/${slug}/posts?limit=20`);
    const base = `https://${domain}${BLOG_PATH}`;
    let xml = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>';
    xml += `<title>Blog | ${siteName}</title><link>${base}/</link>`;
    for (const p of (posts || [])) {
        xml += `<item><title>${esc(p.titulo)}</title><link>${base}/${p.slug}</link>`;
        xml += `<description>${esc(p.extracto || '')}</description></item>`;
    }
    xml += '</channel></rss>';
    return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml' } });
}


// Helpers

async function apiFetch(apiUrl, endpoint) {
    try {
        const r = await fetch(`${apiUrl}${endpoint}`, {
            headers: { 'Accept': 'application/json' },
            cf: { cacheTtl: 3600 },
        });
        if (r.ok) return r.json();
    } catch (e) {
        console.error('BlogEngine fetch error:', e);
    }
    return null;
}

function errorResponse() {
    return new Response('Blog temporalmente no disponible', { status: 503 });
}

function esc(t) {
    return (t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function layout({ title, description, canonical, domain, siteName, content, extraHead = '' }) {
    return `<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${esc(title)}</title>
    <meta name="description" content="${esc(description)}">
    <link rel="canonical" href="${canonical}">
    <meta property="og:title" content="${esc(title)}">
    <meta property="og:description" content="${esc(description)}">
    <meta property="og:url" content="${canonical}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
    ${extraHead}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',sans-serif;line-height:1.7;color:#1f2937}
        .container{max-width:800px;margin:0 auto;padding:0 1.5rem}
        a{color:#2563eb}
        h2{font-size:1.5rem;margin:2rem 0 1rem}
        h3{font-size:1.25rem;margin:1.5rem 0 .75rem}
        p{margin-bottom:1.25rem}
        ul,ol{margin:1rem 0 1.25rem 1.5rem}
        img{max-width:100%;height:auto;border-radius:8px;margin:1.5rem 0}
        header{border-bottom:1px solid #e5e7eb;padding:1rem 0}
        header .c{max-width:1100px;margin:0 auto;padding:0 1.5rem;display:flex;justify-content:space-between;align-items:center}
        .logo{font-size:1.25rem;font-weight:700;color:#2563eb;text-decoration:none}
        nav a{color:#1f2937;text-decoration:none;font-weight:500;margin-left:1.5rem}
        footer{border-top:1px solid #e5e7eb;padding:2rem 0;text-align:center;color:#9ca3af;font-size:.875rem}
    </style>
</head>
<body>
    <header><div class="c">
        <a href="https://${domain}" class="logo">${esc(siteName)}</a>
        <nav><a href="${BLOG_PATH}/">Blog</a><a href="https://${domain}">Sitio Web</a></nav>
    </div></header>
    <main><div class="container" style="padding:2rem 1.5rem">${content}</div></main>
    <footer><div class="container"><p>&copy; ${esc(siteName)}</p></div></footer>
</body>
</html>`;
}
