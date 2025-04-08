from django.urls import path
from .views import (
    UserLoginView,
    HomeView,
    PasswordResetView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('senha/resetar/', PasswordResetView.as_view(), name='password_reset'),
    path('recuperar/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
