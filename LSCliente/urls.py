from django.views.generic import TemplateView
from django.urls import path
from django.contrib.auth import views as auth_views


#import locais
from .forms import NewResetPasswordForm, CustomPasswordResetForm
from . import views

app_name = 'LSCliente'

urlpatterns = [
    path('cliente/', views.ClienteHomeView.as_view, name='clientehome'),
    path('clientelogin/', views.ClienteUserLoginView.as_view(), name='clientelogin'),
    

    #urls para recuperação de conta
path('clientepassword_reset/', auth_views.PasswordResetView.as_view(
    template_name='password_reset/password_reset_email_form.html',
    email_template_name='password_reset/email.html',
    html_email_template_name='password_reset/email.html',
    form_class=CustomPasswordResetForm  
), name='clientepassword_reset'),
path('clientepassword_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset/password_reset_email_enviado.html'), name='clientepassword_reset_done'), #Rota que confirma o envio do email
path('clientepassword_reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset/password_reset_senha_nova_form.html', form_class=NewResetPasswordForm), name='clientepassword_reset_confirm'), #Rota para a tela de redefinir senha
path('clientepassword_reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_senha_trocada.html'), name='clientepassword_reset_complete'), #Rota para a confirmação de senha trocada

]