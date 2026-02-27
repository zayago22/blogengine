<?php
/**
 * BlogEngine Connector para Laravel.
 * 
 * INSTALACIÓN:
 * 1. Copiar este archivo a app/Http/Controllers/BlogEngineController.php
 * 2. Agregar las rutas (ver abajo)
 * 3. Copiar la vista blade
 * 4. Configurar BLOGENGINE_SLUG en .env
 * 
 * RUTAS (agregar a routes/web.php):
 *   Route::get('/blog', [BlogEngineController::class, 'index'])->name('blog.index');
 *   Route::get('/blog/sitemap.xml', [BlogEngineController::class, 'sitemap']);
 *   Route::get('/blog/rss.xml', [BlogEngineController::class, 'rss']);
 *   Route::get('/blog/{slug}', [BlogEngineController::class, 'show'])->name('blog.show');
 * 
 * .ENV:
 *   BLOGENGINE_SLUG=mi-empresa
 *   BLOGENGINE_API_URL=https://blogengine.app
 *   BLOGENGINE_CACHE_TTL=3600
 */

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Http\Response;

class BlogEngineController extends Controller
{
    private string $apiUrl;
    private string $blogSlug;
    private int $cacheTtl;

    public function __construct()
    {
        $this->apiUrl = config('services.blogengine.url', env('BLOGENGINE_API_URL', 'https://blogengine.app'));
        $this->blogSlug = env('BLOGENGINE_SLUG', '');
        $this->cacheTtl = (int) env('BLOGENGINE_CACHE_TTL', 3600);
    }

    /**
     * GET /blog → Lista de artículos.
     */
    public function index()
    {
        $posts = $this->fetch("/api/public/{$this->blogSlug}/posts?limit=20");

        if ($posts === null) {
            abort(503, 'Blog temporalmente no disponible.');
        }

        // SEO meta tags para la home del blog
        $meta = [
            'title' => 'Blog | ' . config('app.name'),
            'description' => 'Artículos y noticias de ' . config('app.name'),
            'canonical' => url('/blog'),
            'og_type' => 'website',
        ];

        return view('blogengine.index', compact('posts', 'meta'));
    }

    /**
     * GET /blog/{slug} → Artículo individual.
     */
    public function show(string $slug)
    {
        $post = $this->fetch("/api/public/{$this->blogSlug}/posts/{$slug}");

        if ($post === null || empty($post)) {
            abort(404);
        }

        // SEO meta tags del artículo
        $meta = [
            'title' => ($post['titulo'] ?? 'Artículo') . ' | ' . config('app.name'),
            'description' => $post['meta_description'] ?? '',
            'canonical' => url("/blog/{$slug}"),
            'og_type' => 'article',
            'og_image' => $post['imagen_destacada_url'] ?? '',
            'article_date' => $post['fecha_publicado'] ?? '',
            'keywords' => $post['keyword'] ?? '',
        ];

        // Schema Article JSON-LD
        $schema = [
            '@context' => 'https://schema.org',
            '@type' => 'Article',
            'headline' => $post['titulo'] ?? '',
            'description' => $post['meta_description'] ?? '',
            'url' => url("/blog/{$slug}"),
            'datePublished' => $post['fecha_publicado'] ?? '',
            'publisher' => [
                '@type' => 'Organization',
                'name' => config('app.name'),
                'url' => url('/'),
            ],
        ];

        return view('blogengine.show', compact('post', 'meta', 'schema'));
    }

    /**
     * GET /blog/sitemap.xml → Sitemap XML.
     */
    public function sitemap()
    {
        $posts = $this->fetch("/api/public/{$this->blogSlug}/posts?limit=100");

        $xml = '<?xml version="1.0" encoding="UTF-8"?>';
        $xml .= '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
        $xml .= '<url><loc>' . url('/blog') . '</loc><changefreq>daily</changefreq><priority>1.0</priority></url>';

        if (is_array($posts)) {
            foreach ($posts as $post) {
                $loc = url('/blog/' . $post['slug']);
                $date = isset($post['fecha_publicado']) ? date('Y-m-d', strtotime($post['fecha_publicado'])) : '';
                $xml .= "<url><loc>{$loc}</loc><lastmod>{$date}</lastmod><priority>0.8</priority></url>";
            }
        }
        $xml .= '</urlset>';

        return response($xml, 200)->header('Content-Type', 'application/xml');
    }

    /**
     * GET /blog/rss.xml → Feed RSS.
     */
    public function rss()
    {
        $posts = $this->fetch("/api/public/{$this->blogSlug}/posts?limit=20");
        $name = config('app.name');

        $xml = '<?xml version="1.0" encoding="UTF-8"?>';
        $xml .= '<rss version="2.0"><channel>';
        $xml .= "<title>Blog | {$name}</title><link>" . url('/blog') . "</link>";

        if (is_array($posts)) {
            foreach ($posts as $post) {
                $loc = url('/blog/' . $post['slug']);
                $title = htmlspecialchars($post['titulo'] ?? '', ENT_XML1);
                $desc = htmlspecialchars($post['extracto'] ?? '', ENT_XML1);
                $xml .= "<item><title>{$title}</title><link>{$loc}</link><description>{$desc}</description></item>";
            }
        }
        $xml .= '</channel></rss>';

        return response($xml, 200)->header('Content-Type', 'application/rss+xml');
    }

    /**
     * Fetch con cache.
     */
    private function fetch(string $endpoint): ?array
    {
        $cacheKey = 'blogengine_' . md5($endpoint);

        return Cache::remember($cacheKey, $this->cacheTtl, function () use ($endpoint) {
            try {
                $response = Http::timeout(10)
                    ->acceptJson()
                    ->get($this->apiUrl . $endpoint);

                if ($response->successful()) {
                    return $response->json();
                }
            } catch (\Exception $e) {
                report($e);
            }
            return null;
        });
    }
}
