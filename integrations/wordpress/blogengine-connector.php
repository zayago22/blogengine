<?php
/**
 * Plugin Name: BlogEngine Connector
 * Plugin URI: https://blogengine.app
 * Description: Conecta tu WordPress con BlogEngine para servir artículos SEO-optimizados.
 * Version: 1.0.0
 * Author: BlogEngine
 * Text Domain: blogengine
 * 
 * INSTALACIÓN:
 * 1. Subir esta carpeta a wp-content/plugins/
 * 2. Activar el plugin desde el admin de WordPress
 * 3. Ir a Ajustes → BlogEngine
 * 4. Pegar el Blog Slug (ej: "raiz-rentable")
 * 5. Listo — el blog aparece en tudominio.com/blog
 * 
 * SEO:
 * - Renderiza HTML server-side (Google lo ve perfecto)
 * - Meta tags, Open Graph, canonical → todo del dominio del cliente
 * - Sitemap integrado con el sitemap de WordPress
 * - Schema markup Article incluido
 * - El link juice se queda en el dominio del cliente ✅
 */

if (!defined('ABSPATH')) exit;

// =============================================================================
// CONSTANTES
// =============================================================================

define('BLOGENGINE_VERSION', '1.0.0');
define('BLOGENGINE_API_URL', 'https://blogengine.app');
define('BLOGENGINE_CACHE_TIME', 3600); // 1 hora de cache

// =============================================================================
// CONFIGURACIÓN (Admin → Ajustes → BlogEngine)
// =============================================================================

add_action('admin_menu', function() {
    add_options_page(
        'BlogEngine', 
        'BlogEngine', 
        'manage_options', 
        'blogengine', 
        'blogengine_settings_page'
    );
});

add_action('admin_init', function() {
    register_setting('blogengine_settings', 'blogengine_slug');
    register_setting('blogengine_settings', 'blogengine_api_url');
    register_setting('blogengine_settings', 'blogengine_path');
    register_setting('blogengine_settings', 'blogengine_cache_time');
});

function blogengine_settings_page() {
    $slug = get_option('blogengine_slug', '');
    $api_url = get_option('blogengine_api_url', BLOGENGINE_API_URL);
    $path = get_option('blogengine_path', 'blog');
    $cache_time = get_option('blogengine_cache_time', BLOGENGINE_CACHE_TIME);
    ?>
    <div class="wrap">
        <h1>BlogEngine — Configuración</h1>
        <form method="post" action="options.php">
            <?php settings_fields('blogengine_settings'); ?>
            <table class="form-table">
                <tr>
                    <th>Blog Slug</th>
                    <td>
                        <input type="text" name="blogengine_slug" value="<?php echo esc_attr($slug); ?>" class="regular-text" placeholder="mi-empresa">
                        <p class="description">El slug de tu blog en BlogEngine (ej: "raiz-rentable")</p>
                    </td>
                </tr>
                <tr>
                    <th>Ruta del blog</th>
                    <td>
                        <code><?php echo home_url('/'); ?></code>
                        <input type="text" name="blogengine_path" value="<?php echo esc_attr($path); ?>" style="width:150px" placeholder="blog">
                        <p class="description">El blog aparecerá en: <?php echo home_url('/' . $path); ?></p>
                    </td>
                </tr>
                <tr>
                    <th>URL API BlogEngine</th>
                    <td>
                        <input type="text" name="blogengine_api_url" value="<?php echo esc_attr($api_url); ?>" class="regular-text">
                        <p class="description">Normalmente no necesitas cambiar esto</p>
                    </td>
                </tr>
                <tr>
                    <th>Cache (segundos)</th>
                    <td>
                        <input type="number" name="blogengine_cache_time" value="<?php echo esc_attr($cache_time); ?>" style="width:100px">
                        <p class="description">Tiempo de cache para las peticiones (3600 = 1 hora)</p>
                    </td>
                </tr>
            </table>
            <?php submit_button('Guardar'); ?>
        </form>
        
        <?php if ($slug): ?>
        <h2>Estado de la conexión</h2>
        <?php
        $test = blogengine_fetch("/api/public/{$slug}/posts?limit=1");
        if ($test !== false && is_array($test)):
        ?>
            <p style="color:green;">✅ Conectado correctamente. <?php echo count($test); ?> artículo(s) disponibles.</p>
            <p>
                <a href="<?php echo home_url('/' . $path); ?>" target="_blank" class="button">
                    Ver Blog →
                </a>
            </p>
        <?php else: ?>
            <p style="color:red;">❌ No se pudo conectar. Verifica el slug y la URL de la API.</p>
        <?php endif; ?>
        <?php endif; ?>
    </div>
    <?php
}

// =============================================================================
// REWRITE RULES — Crea las rutas /blog y /blog/slug-del-post
// =============================================================================

add_action('init', function() {
    $path = get_option('blogengine_path', 'blog');
    
    // /blog → lista de artículos
    add_rewrite_rule(
        "^{$path}/?$",
        'index.php?blogengine_page=home',
        'top'
    );
    
    // /blog/slug-del-articulo → artículo individual
    add_rewrite_rule(
        "^{$path}/([^/]+)/?$",
        'index.php?blogengine_page=post&blogengine_post_slug=$matches[1]',
        'top'
    );
    
    // /blog/sitemap.xml
    add_rewrite_rule(
        "^{$path}/sitemap\.xml$",
        'index.php?blogengine_page=sitemap',
        'top'
    );
    
    // /blog/rss.xml
    add_rewrite_rule(
        "^{$path}/rss\.xml$",
        'index.php?blogengine_page=rss',
        'top'
    );
});

add_filter('query_vars', function($vars) {
    $vars[] = 'blogengine_page';
    $vars[] = 'blogengine_post_slug';
    return $vars;
});

// Flush rewrite rules al activar/desactivar plugin
register_activation_hook(__FILE__, function() {
    flush_rewrite_rules();
});
register_deactivation_hook(__FILE__, function() {
    flush_rewrite_rules();
});

// =============================================================================
// TEMPLATE — Renderiza las páginas del blog
// =============================================================================

add_action('template_redirect', function() {
    $page = get_query_var('blogengine_page');
    if (!$page) return;
    
    $slug = get_option('blogengine_slug', '');
    if (!$slug) {
        wp_die('BlogEngine no configurado. Ve a Ajustes → BlogEngine.');
    }
    
    switch ($page) {
        case 'home':
            blogengine_render_home($slug);
            break;
        case 'post':
            $post_slug = get_query_var('blogengine_post_slug');
            blogengine_render_post($slug, $post_slug);
            break;
        case 'sitemap':
            blogengine_render_sitemap($slug);
            break;
        case 'rss':
            blogengine_render_rss($slug);
            break;
    }
    exit;
});

// =============================================================================
// RENDERIZADORES
// =============================================================================

function blogengine_render_home($blog_slug) {
    $posts = blogengine_fetch("/api/public/{$blog_slug}/posts?limit=20");
    if ($posts === false) {
        status_header(503);
        wp_die('Blog temporalmente no disponible.');
    }
    
    $path = get_option('blogengine_path', 'blog');
    $site_name = get_bloginfo('name');
    
    // Usar el tema de WordPress (header + footer del tema activo)
    get_header();
    ?>
    <div class="blogengine-container" style="max-width:800px;margin:2rem auto;padding:0 1.5rem;">
        <h1 style="font-size:2rem;margin-bottom:2rem;">Blog</h1>
        
        <?php if (empty($posts)): ?>
            <p>Próximamente publicaremos contenido aquí.</p>
        <?php else: ?>
            <?php foreach ($posts as $post): ?>
                <article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">
                    <h2 style="margin-bottom:0.5rem;">
                        <a href="<?php echo home_url("/{$path}/" . $post['slug']); ?>" style="color:inherit;text-decoration:none;">
                            <?php echo esc_html($post['titulo']); ?>
                        </a>
                    </h2>
                    <?php if (!empty($post['fecha_publicado'])): ?>
                        <div style="color:#888;font-size:0.875rem;margin-bottom:0.75rem;">
                            <?php echo date_i18n('j \d\e F, Y', strtotime($post['fecha_publicado'])); ?>
                        </div>
                    <?php endif; ?>
                    <p><?php echo esc_html($post['extracto'] ?? ''); ?></p>
                    <a href="<?php echo home_url("/{$path}/" . $post['slug']); ?>" style="color:#2563eb;font-weight:500;">
                        Leer más →
                    </a>
                </article>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
    <?php
    get_footer();
}

function blogengine_render_post($blog_slug, $post_slug) {
    $post = blogengine_fetch("/api/public/{$blog_slug}/posts/{$post_slug}");
    if ($post === false || empty($post)) {
        status_header(404);
        wp_die('Artículo no encontrado.', 'Not Found', ['response' => 404]);
    }
    
    $path = get_option('blogengine_path', 'blog');
    $canonical = home_url("/{$path}/{$post_slug}");
    
    // Inyectar meta tags SEO en el <head>
    add_action('wp_head', function() use ($post, $canonical) {
        echo '<meta name="description" content="' . esc_attr($post['meta_description'] ?? '') . '">' . "\n";
        echo '<link rel="canonical" href="' . esc_url($canonical) . '">' . "\n";
        echo '<meta property="og:title" content="' . esc_attr($post['titulo']) . '">' . "\n";
        echo '<meta property="og:description" content="' . esc_attr($post['meta_description'] ?? '') . '">' . "\n";
        echo '<meta property="og:url" content="' . esc_url($canonical) . '">' . "\n";
        echo '<meta property="og:type" content="article">' . "\n";
        if (!empty($post['imagen_destacada_url'])) {
            echo '<meta property="og:image" content="' . esc_url($post['imagen_destacada_url']) . '">' . "\n";
        }
        echo '<meta name="twitter:card" content="summary_large_image">' . "\n";
        
        // Schema Article JSON-LD
        $schema = [
            '@context' => 'https://schema.org',
            '@type' => 'Article',
            'headline' => $post['titulo'],
            'description' => $post['meta_description'] ?? '',
            'url' => $canonical,
            'datePublished' => $post['fecha_publicado'] ?? '',
            'publisher' => [
                '@type' => 'Organization',
                'name' => get_bloginfo('name'),
                'url' => home_url(),
            ],
        ];
        echo '<script type="application/ld+json">' . json_encode($schema, JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
    });
    
    // Override del título de la página
    add_filter('pre_get_document_title', function() use ($post) {
        return $post['titulo'] . ' | ' . get_bloginfo('name');
    });
    
    get_header();
    ?>
    <article class="blogengine-article" style="max-width:800px;margin:2rem auto;padding:0 1.5rem;">
        <h1 style="font-size:2.25rem;line-height:1.3;margin-bottom:1rem;">
            <?php echo esc_html($post['titulo']); ?>
        </h1>
        
        <?php if (!empty($post['fecha_publicado'])): ?>
            <div style="color:#888;margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid #eee;">
                <?php echo date_i18n('j \d\e F, Y', strtotime($post['fecha_publicado'])); ?>
            </div>
        <?php endif; ?>
        
        <div class="blogengine-content" style="line-height:1.8;">
            <?php echo wp_kses_post($post['contenido_html'] ?? ''); ?>
        </div>
        
        <div style="margin-top:2rem;">
            <a href="<?php echo home_url("/{$path}"); ?>" style="color:#2563eb;">← Volver al blog</a>
        </div>
    </article>
    <?php
    get_footer();
}

function blogengine_render_sitemap($blog_slug) {
    $posts = blogengine_fetch("/api/public/{$blog_slug}/posts?limit=100");
    $path = get_option('blogengine_path', 'blog');
    
    header('Content-Type: application/xml; charset=UTF-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
    echo "  <url><loc>" . home_url("/{$path}") . "</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n";
    
    if (is_array($posts)) {
        foreach ($posts as $post) {
            $url = home_url("/{$path}/" . $post['slug']);
            $date = !empty($post['fecha_publicado']) ? date('Y-m-d', strtotime($post['fecha_publicado'])) : '';
            echo "  <url><loc>{$url}</loc><lastmod>{$date}</lastmod><priority>0.8</priority></url>\n";
        }
    }
    echo '</urlset>';
}

function blogengine_render_rss($blog_slug) {
    $posts = blogengine_fetch("/api/public/{$blog_slug}/posts?limit=20");
    $path = get_option('blogengine_path', 'blog');
    $site_name = get_bloginfo('name');
    
    header('Content-Type: application/rss+xml; charset=UTF-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    echo '<rss version="2.0"><channel>' . "\n";
    echo "<title>Blog | {$site_name}</title>\n";
    echo "<link>" . home_url("/{$path}") . "</link>\n";
    
    if (is_array($posts)) {
        foreach ($posts as $post) {
            $url = home_url("/{$path}/" . $post['slug']);
            echo "<item><title>" . esc_html($post['titulo']) . "</title>";
            echo "<link>{$url}</link>";
            echo "<description>" . esc_html($post['extracto'] ?? '') . "</description></item>\n";
        }
    }
    echo '</channel></rss>';
}

// =============================================================================
// FETCH CON CACHE
// =============================================================================

function blogengine_fetch($endpoint) {
    $api_url = get_option('blogengine_api_url', BLOGENGINE_API_URL);
    $cache_time = (int) get_option('blogengine_cache_time', BLOGENGINE_CACHE_TIME);
    $cache_key = 'be_' . md5($endpoint);
    
    // Intentar cache
    $cached = get_transient($cache_key);
    if ($cached !== false) {
        return $cached;
    }
    
    // Fetch
    $response = wp_remote_get($api_url . $endpoint, [
        'timeout' => 10,
        'headers' => ['Accept' => 'application/json'],
    ]);
    
    if (is_wp_error($response)) {
        return false;
    }
    
    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        return false;
    }
    
    // Guardar en cache
    set_transient($cache_key, $data, $cache_time);
    
    return $data;
}

// =============================================================================
// INTEGRAR CON SITEMAP DE WORDPRESS (Yoast, Rank Math, etc.)
// =============================================================================

// Para Yoast SEO
add_filter('wpseo_sitemap_index', function($sitemap_index) {
    $path = get_option('blogengine_path', 'blog');
    $sitemap_url = home_url("/{$path}/sitemap.xml");
    $sitemap_index .= '<sitemap><loc>' . $sitemap_url . '</loc></sitemap>';
    return $sitemap_index;
});

// Agregar link al blog en el menú de navegación
add_filter('wp_nav_menu_items', function($items, $args) {
    $path = get_option('blogengine_path', 'blog');
    $slug = get_option('blogengine_slug', '');
    if ($slug && $args->theme_location === 'primary') {
        $items .= '<li class="menu-item"><a href="' . home_url("/{$path}") . '">Blog</a></li>';
    }
    return $items;
}, 10, 2);
