# URLs do Dashboard
from django.urls import path
from django.contrib.auth import views as auth_views

# Importações locais
from .forms import NewResetPasswordForm, CustomPasswordResetForm
from . import views


urlpatterns = [
    # Página inicial do dashboard
    path('', views.HomeView.as_view(), name='home'),
    
    # Sistema de autenticação
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.cliente_custom_logout_view, name='logout'),
    
    # Gestão de colaboradores
    path('GestaoColaborador/', views.CollabManage.as_view(), name='collabmanage'),
    path('RegistroColaborador/', views.CollabRegisterView.as_view(), name='collabregister'),
    
    # Gestão de clientes
    path('ClienteRegister/', views.CadastroClienteView.as_view(), name='ClienteRegister'),
    path('ClienteEdit/', views.EditarClienteView.as_view(), name='ClienteEdit'),
    
    # Sistema de questões/perguntas
    path('questoes/', views.QuestaoManageView.as_view(), name='questao_manage'),
    
    # Configurações e administração
    path('configuracao-sistema/', views.ConfiguracaoSistemaView.as_view(), name='configuracao_sistema'),
    path('encerrar-sessao/<int:sessao_id>/', views.EncerrarSessaoUsuarioView.as_view(), name='encerrar_sessao'),

    # Sistema de recuperação de senha
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='password_reset/password_reset_email_form.html',
             email_template_name='password_reset/email.html',
             html_email_template_name='password_reset/email.html',
             form_class=CustomPasswordResetForm
         ), 
         name='password_reset'),
    
    path('password_reset_done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset/password_reset_email_enviado.html'
         ), 
         name='password_reset_done'),
    
    path('password_reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password_reset/password_reset_senha_nova_form.html', 
             form_class=NewResetPasswordForm
         ), 
         name='password_reset_confirm'),
    
    path('password_reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset/password_reset_senha_trocada.html'
         ), 
         name='password_reset_complete'),
]