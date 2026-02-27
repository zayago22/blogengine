{{-- resources/views/blogengine/index.blade.php --}}
{{-- Extiende tu layout principal de Laravel --}}
@extends('layouts.app')

@section('title', $meta['title'])

@section('meta')
    <meta name="description" content="{{ $meta['description'] }}">
    <link rel="canonical" href="{{ $meta['canonical'] }}">
    <meta property="og:title" content="{{ $meta['title'] }}">
    <meta property="og:description" content="{{ $meta['description'] }}">
    <meta property="og:url" content="{{ $meta['canonical'] }}">
    <meta property="og:type" content="{{ $meta['og_type'] }}">
@endsection

@section('content')
<div style="max-width:800px;margin:2rem auto;padding:0 1.5rem;">
    <h1 style="font-size:2rem;margin-bottom:2rem;">Blog</h1>

    @forelse($posts as $post)
        <article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">
            <h2 style="margin-bottom:0.5rem;">
                <a href="{{ route('blog.show', $post['slug']) }}" style="color:inherit;text-decoration:none;">
                    {{ $post['titulo'] }}
                </a>
            </h2>
            @if(!empty($post['fecha_publicado']))
                <div style="color:#888;font-size:0.875rem;margin-bottom:0.75rem;">
                    {{ \Carbon\Carbon::parse($post['fecha_publicado'])->translatedFormat('j \\d\\e F, Y') }}
                </div>
            @endif
            <p>{{ $post['extracto'] ?? '' }}</p>
            <a href="{{ route('blog.show', $post['slug']) }}" style="color:#2563eb;font-weight:500;">
                Leer más →
            </a>
        </article>
    @empty
        <p style="text-align:center;color:#999;padding:4rem 0;">Próximamente publicaremos contenido aquí.</p>
    @endforelse
</div>
@endsection
