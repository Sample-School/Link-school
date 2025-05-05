# No arquivo urls.py
from django.views.generic import TemplateView
from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

# import locais
from LSCliente.forms import NewResetPasswordForm, CustomPasswordResetForm
from LSCliente import views
from LSCliente.views import TenantAwarePasswordResetConfirmView  # Adicione esta importação

app_name = 'LSCliente'

urlpatterns = [
    path('cliente/', views.ClienteHomeView.as_view(), name='clientehome'),
    path('clientelogin/', views.ClienteUserLoginView.as_view(), name='clientelogin'),

    # urls para recuperação de conta - ATUALIZADO
    path('clientepassword_reset/', views.TenantPasswordResetView.as_view(
        template_name='cliente_password_reset/password_reset_email_form.html',
        email_template_name='cliente_password_reset/email.html',
        html_email_template_name='cliente_password_reset/email.html',
        form_class=CustomPasswordResetForm,
        success_url=reverse_lazy('LSCliente:clientepassword_reset_done')
    ), name='clientepassword_reset'),

    path('clientepassword_reset_done/', auth_views.PasswordResetDoneView.as_view(
        template_name='cliente_password_reset/password_reset_email_enviado.html'
    ), name='clientepassword_reset_done'),

    path('clientepassword_reset/<uidb64>/<token>/', views.TenantAwarePasswordResetConfirmView.as_view(), 
    name='clientepassword_reset_confirm'),

    path('clientepassword_reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='cliente_password_reset/password_reset_senha_trocada.html'
    ), name='clientepassword_reset_complete'),
]