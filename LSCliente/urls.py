# URLs do módulo LSCliente
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

# Imports das views e forms do app
from LSCliente.forms import CustomPasswordResetForm
from LSCliente import views

app_name = 'LSCliente'

urlpatterns = [
    # Dashboard principal do cliente
    path('home/', views.ClienteHomeView.as_view(), name='clientehome'),
    
    # Autenticação
    path('clientelogin/', views.ClienteUserLoginView.as_view(), name='clientelogin'),
    path('logout/', views.custom_logout_view, name='clientelogout'),
    
    # Gerenciamento de usuários
    path('CLUserMange/', views.ClienteUserMangeView.as_view(), name='CLUserMange'),
    path('CLUserList/', views.ClienteUserListView.as_view(), name='CLUserList'),
    path('CLUserToggleStatus/<int:pk>/', views.ClienteUserToggleStatusView.as_view(), name='CLUserToggleStatus'),
    
    # Funcionalidades principais
    path('CLProvaCreate/', views.ClienteProvaCreateView.as_view(), name='CLProvaCreate'),
    path('CLParametros/', views.ClienteParametroView.as_view(), name='CLParametros'),
    

    # Sistema de recuperação de senha
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