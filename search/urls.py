
from django.urls import path
from .views import YoutubeSearchView

urlpatterns = [
    # ... your other URL patterns ...
    path('api/youtube-search/', YoutubeSearchView.as_view(), name='youtube-search'),
]