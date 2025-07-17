from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework import status
import yt_dlp

class YoutubeSearchView(APIView):
    """
    API view for searching YouTube videos using yt-dlp
    """
    parser_classes = (JSONParser,)

    def get_best_thumbnail(self, thumbnails):
        if not thumbnails:
            return None
        
        # Sort thumbnails by width and height to get the highest resolution
        sorted_thumbnails = sorted(
            thumbnails,
            key=lambda x: (x.get('width', 0), x.get('height', 0)),
            reverse=True
        )
        return sorted_thumbnails[0]['url'] if sorted_thumbnails else None

    def post(self, request):
        try:
            # Get search parameters from request
            search_query = request.data.get('query')
            max_results = request.data.get('max_results', 10)  # Default to 10 results
            
            if not search_query:
                return Response(
                    {'error': 'Search query is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Do not download videos
                'default_search': 'ytsearch',  # Use YouTube search
                'ignoreerrors': True,
            }

            # Perform the search
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Construct search query with max results
                full_query = f"ytsearch{max_results}:{search_query}"
                results = ydl.extract_info(full_query, download=False)

                # Process results
                videos = []
                if results and 'entries' in results:
                    for entry in results['entries']:
                        if entry:
                            video_data = {
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'url': entry.get('url'),
                                'thumbnail': self.get_best_thumbnail(entry.get('thumbnails')),
                                'duration': entry.get('duration'),
                                'channel': entry.get('uploader'),
                                'channel_url': entry.get('channel_url'),
                                'view_count': entry.get('view_count'),
                            }
                            videos.append(video_data)

                return Response({
                    'query': search_query,
                    'results_count': len(videos),
                    'videos': videos
                })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )