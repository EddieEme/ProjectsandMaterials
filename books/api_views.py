import logging
import requests
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Book

logger = logging.getLogger(__name__)



@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 15)
def book_preview(request, id):
    """
    Get book preview and statistics.
    Example: /api/books/623/preview/
    """
    try:
        book = get_object_or_404(Book.objects.only('id', 'title', 'preview_url'), id=id)

        stats_cache_key = f"book_{id}_stats"
        stats = cache.get(stats_cache_key)
        if not stats:
            try:
                stats = book.get_file_statistics()
            except Exception as e:
                logger.warning(f"Statistics error for book {id}: {e}")
                stats = {"pages": 0, "words": 0}
            cache.set(stats_cache_key, stats, 60 * 60 * 24)

        return Response({
            'id': book.id,
            'title': book.title,
            'preview_url': book.preview_url,
            'stats': stats
        })

    except Exception as e:
        logger.exception("Book preview error")
        return Response({"error": "Could not load book preview"}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def book_details_api(request, slug):
    """
    Backward-compatible version of book stats API.
    Example: /api/book/623/details/
    """
    book = get_object_or_404(Book.objects.only('slug', 'preview_url'), slug=slug)

    stats_cache_key = f"book_stats_{book.slug}"
    stats = cache.get(stats_cache_key)
    if not stats:
        try:
            stats = book.get_file_statistics()
        except Exception as e:
            logger.warning(f"Stat calculation error for book {id}: {e}")
            stats = {"pages": 0, "words": 0}
        cache.set(stats_cache_key, stats, 60 * 60 * 24)

    return JsonResponse({
        'preview_url': book.preview_url,
        'page_count': stats.get('pages'),
        'word_count': stats.get('words'),
        'status': 'success'
    })


@api_view(['GET'])
def health_check(request):
    """
    Service health check endpoint.
    Example: /api/health/
    """
    return Response({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Book API',
        'version': '1.0.0'
    })
