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

# YouTube API Configuration
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/"
DEFAULT_CACHE_TIMEOUT = 60 * 60 * 2  # 2 hours

@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(DEFAULT_CACHE_TIMEOUT)
def most_viewed_videos(request, channel_id):
    """
    Get most viewed videos for a YouTube channel.
    Example: /api/most-viewed-videos/UCaB3YPxB_eXqTcFdFo9CrCA/?max_results=3
    """
    try:
        max_results = int(request.query_params.get('max_results', 3))
        if not (1 <= max_results <= 50):
            return Response({"error": "max_results must be between 1-50"}, status=400)

        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
        if not api_key:
            logger.error("YouTube API key missing")
            return Response({"error": "YouTube service unavailable"}, status=503)

        search_params = {
            'part': 'snippet',
            'channelId': channel_id,
            'order': 'viewCount',
            'type': 'video',
            'maxResults': max_results,
            'key': api_key
        }

        search_response = requests.get(f"{YOUTUBE_API_URL}search", params=search_params)
        search_response.raise_for_status()

        video_items = search_response.json().get('items', [])
        if not video_items:
            return Response({"error": "No videos found"}, status=404)

        video_ids = [item['id']['videoId'] for item in video_items]
        stats_response = requests.get(
            f"{YOUTUBE_API_URL}videos",
            params={'part': 'statistics', 'id': ','.join(video_ids), 'key': api_key}
        )
        stats_response.raise_for_status()

        stats_data = stats_response.json().get('items', [])
        videos = []
        for item, stats in zip(video_items, stats_data):
            videos.append({
                'id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt'],
                'thumbnail': item['snippet']['thumbnails']['high']['url'],
                'views': int(stats['statistics']['viewCount']),
                'likes': int(stats['statistics'].get('likeCount', 0)),
                'comments': int(stats['statistics'].get('commentCount', 0)),
            })

        return Response({
            'channel_id': channel_id,
            'count': len(videos),
            'videos': videos
        })

    except ValueError:
        return Response({"error": "Invalid max_results"}, status=400)
    except requests.exceptions.RequestException as e:
        logger.error(f"YouTube API request failed: {e}")
        return Response({"error": "YouTube API request failed"}, status=503)
    except Exception as e:
        logger.exception("Unexpected error")
        return Response({"error": "Internal server error"}, status=500)


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
def book_details_api(request, id):
    """
    Backward-compatible version of book stats API.
    Example: /api/book/623/details/
    """
    book = get_object_or_404(Book.objects.only('id', 'preview_url'), id=id)

    stats_cache_key = f"book_stats_{book.id}"
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
