from django.http import JsonResponse, FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework import status
import yt_dlp
import json
import os
import uuid
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TPE1, TIT2

class YoutubeDLView(APIView):
    """
    API view for fetching video information using yt-dlp
    """
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    
    def add_metadata(self, file_path, info):
        try:
            # Load or create ID3 tag
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()

            # Add title if available
            if info.get('title'):
                audio.tags.add(TIT2(encoding=3, text=info['title']))

            # Add artist/creator if available
            if info.get('uploader'):
                audio.tags.add(TPE1(encoding=3, text=info['uploader']))

            # Add thumbnail if available
            if info.get('thumbnail'):
                try:
                    thumbnail_data = requests.get(info['thumbnail']).content
                    audio.tags.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=thumbnail_data
                    ))
                except:
                    pass  # Skip thumbnail if there's any issue

            audio.save()
        except Exception as e:
            print(f"Error adding metadata: {str(e)}")

    def get(self, request):
        temp_path = None
        final_path = None
        file_handle = None

        try:
            url = request.GET.get('url')
            if not url:
                return Response(
                    {'error': 'URL parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ensure downloads directory exists
            os.makedirs('downloads', exist_ok=True)

            # Generate a unique filename using UUID to avoid conflicts
            temp_filename = f"{uuid.uuid4()}.mp3"
            temp_path = os.path.join('downloads', temp_filename)

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': temp_path.rsplit('.', 1)[0],
                'quiet': True,
                'no_warnings': True
            }

            # Download and convert to MP3
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            # Add metadata
            self.add_metadata(temp_path, info)

            # Create safe title for the final filename
            safe_title = "".join(c for c in info.get('title', 'audio') 
                            if c.isalnum() or c in (' ', '-', '_')).strip()
            final_filename = f"{safe_title}.mp3"
            final_path = os.path.join('downloads', final_filename)

            # Rename the file
            try:
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(temp_path, final_path)
            except Exception as e:
                final_path = temp_path  # Fallback to temp path if rename fails

            # Open file and create response
            file_handle = open(final_path, 'rb')
            response = FileResponse(
                file_handle,
                content_type='audio/mpeg',
                as_attachment=True,
                filename=final_filename
            )

            # Use FileResponse's built-in file closure
            return response

        except Exception as e:
            # Close file handle if it's open
            if file_handle:
                file_handle.close()
            
            # Clean up files
            for path in [temp_path, final_path]:
                if path and os.path.exists(path):
                    os.remove(path)

            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )