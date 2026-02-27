{{-- resources/views/blogengine/show.blade.php --}}
@extends('layouts.app')

@section('title', $meta['title'])

@section('meta')
    <meta name="description" content="{{ $meta['description'] }}">
    <link rel="canonical" href="{{ $meta['canonical'] }}">
    <meta property="og:title" content="{{ $meta['title'] }}">
    <meta property="og:description" content="{{ $meta['description'] }}">
    <meta property="og:url" content="{{ $meta['canonical'] }}">
    <meta property="og:type" content="{{ $meta['og_type'] }}">
    @if(!empty($meta['og_image']))
        <meta property="og:image" content="{{ $meta['og_image'] }}">
    @endif
    @if(!empty($meta['keywords']))
        <meta name="keywords" content="{{ $meta['keywords'] }}">
    @endif
    <meta name="twitter:card" content="summary_large_image">
    <script type="application/ld+json">{!! json_encode($schema, JSON_UNESCAPED_UNICODE) !!}</script>
@endsection

@section('content')
<article style="max-width:800px;margin:2rem auto;padding:0 1.5rem;">
    <h1 style="font-size:2.25rem;line-height:1.3;margin-bottom:1rem;">
        {{ $post['titulo'] }}
    </h1>

    @if(!empty($post['fecha_publicado']))
        <div style="color:#888;margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid #eee;">
            {{ \Carbon\Carbon::parse($post['fecha_publicado'])->translatedFormat('j \\d\\e F, Y') }}
        </div>
    @endif

    <div class="blogengine-content" style="line-height:1.8;">
        {!! $post['contenido_html'] ?? '' !!}
    </div>

    <div style="margin-top:2rem;">
        <a href="{{ route('blog.index') }}" style="color:#2563eb;">← Volver al blog</a>
    </div>
</article>
@endsection
