import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Category, Book
from .serializers import CategorySerializer, BookSerializer
import requests
import requests
import os

import logging
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def most_viewed_videos(request, channel_id):
    """
    API endpoint to fetch the most viewed videos from a YouTube channel.
    """
    # Step 1: Validate inputs
    try:
        max_results = int(request.query_params.get('max_results', 3))
        if max_results <= 0 or max_results > 50:
            return Response(
                {"error": "max_results must be between 1 and 50."},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {"error": "max_results must be a valid integer."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Step 2: Fetch most viewed videos
    try:
        # Use environment variable for API key
        api_key = settings.YOUTUBE_API_KEY
        if not api_key:
            logger.error("YouTube API key is not configured.")
            return Response(
                {"error": "YouTube API key is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Fetch video IDs and details
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&order=viewCount&type=video&maxResults={max_results}&key={api_key}"
        search_response = requests.get(search_url)
        search_response.raise_for_status()
        video_items = search_response.json().get("items", [])

        if not video_items:
            return Response(
                {"error": "No videos found for this channel."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch video statistics
        video_ids = [video["id"]["videoId"] for video in video_items]
        stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={','.join(video_ids)}&key={api_key}"
        stats_response = requests.get(stats_url)
        stats_response.raise_for_status()
        stats_data = stats_response.json().get("items", [])

        # Combine video data with statistics
        videos_with_stats = []
        for video, stats in zip(video_items, stats_data):
            videos_with_stats.append({
                "videoId": video["id"]["videoId"],
                "title": video["snippet"]["title"],
                "description": video["snippet"]["description"],
                "publishedAt": video["snippet"]["publishedAt"],
                "thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                "viewCount": stats["statistics"]["viewCount"],
                "likeCount": stats["statistics"].get("likeCount", 0),
                "commentCount": stats["statistics"].get("commentCount", 0),
            })

        return Response({"videos": videos_with_stats}, status=status.HTTP_200_OK)

    except requests.exceptions.HTTPError as e:
        logger.error(f"YouTube API HTTP error: {str(e)}")
        return Response(
            {"error": f"YouTube API error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"YouTube API request error: {str(e)}")
        return Response(
            {"error": f"YouTube API request error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response(
            {"error": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        
        
