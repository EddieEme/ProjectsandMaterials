from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from decouple import config

API_KEY = config('API_KEY')

class MostViewedVideos(APIView):
    """
    API endpoint to fetch the most viewed videos from a YouTube channel.
    """
    authentication_classes = []  # Disable authentication
    permission_classes = []      # Allow access to anyone

    def get(self, request, channel_id):
        max_results = request.query_params.get('max_results', 3)  # Default to 3 videos

        try:
            # Step 1: Fetch most viewed videos
            search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&order=viewCount&type=video&maxResults={max_results}&key={API_KEY}"
            search_response = requests.get(search_url)
            search_response.raise_for_status()
            video_items = search_response.json().get("items", [])

            if not video_items:
                return Response({"error": "No videos found for this channel."}, status=status.HTTP_404_NOT_FOUND)

            # Step 2: Get video statistics
            video_ids = [video["id"]["videoId"] for video in video_items]
            stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={','.join(video_ids)}&key={API_KEY}"
            stats_response = requests.get(stats_url)
            stats_response.raise_for_status()
            stats_data = stats_response.json().get("items", [])

            # Step 3: Combine video data with statistics
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

        except requests.exceptions.RequestException as e:
            return Response({"error": f"YouTube API error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)