from .views import UserLoginView,HomeView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path



urlpatterns = [
    path('login/', UserLoginView.as_view(),name='login'),
    path('', HomeView.as_view(),name='home'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)