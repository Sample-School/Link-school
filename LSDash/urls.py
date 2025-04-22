from django.views.generic import TemplateView
from django.urls import path
from django.contrib.auth import views as auth_views


#import locais
from .forms import NewResetPasswordForm
from . import views
from LSDash.views import EditarClienteView

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('GestaoColaborador/', views.CollabManage.as_view(), name='collabmanage'),
    path('RegistroColaborador/', views.CollabRegisterView.as_view(), name='collabregister'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('ClienteRegister/', views.CadastroClienteView.as_view(), name='ClienteRegister'),
    #urls para recuperação de conta
path('password_reset/', auth_views.PasswordResetView.as_view(
    template_name='password_reset/password_reset_email_form.html',
    email_template_name='password_reset/email.html',
    html_email_template_name='password_reset/email.html'  # Adicione esta linha
), name='password_reset'),# URL DO FORM 
path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset/password_reset_email_enviado.html'), name='password_reset_done'), #Rota que confirma o envio do email
path('password_reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset/password_reset_senha_nova_form.html', form_class=NewResetPasswordForm), name='password_reset_confirm'), #Rota para a tela de redefinir senha
path('password_reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_senha_trocada.html'), name='password_reset_complete'), #Rota para a confirmação de senha trocada
# urls de editar cliente.
path('ClienteEdit/', views.EditarClienteView.as_view(), name='ClienteEdit'),
path('ClienteEdit/', EditarClienteView.as_view(), name='EditarCliente'),
]



