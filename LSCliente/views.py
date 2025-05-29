from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy,  reverse
from django.contrib import messages
from django.views.generic import TemplateView, View, CreateView,  ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .forms import NewResetPasswordForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .forms import UserLoginForm
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db import IntegrityError
from django_tenants.utils import tenant_context
from django.utils.text import slugify
from django import forms
from django.utils import timezone
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.db.models import Q
from django.contrib.sessions.models import Session


from .forms import CustomPasswordResetForm, UsuarioClienteForm, ClienteSystemSettingsForm
from .models import UsuarioCliente, ClienteSystemSettings, SessaoUsuarioCliente



class ClienteUserLoginView(LoginView):
    template_name = "clienteLogin.html"
    success_url = reverse_lazy('LSCliente:clientehome')
    form_class = UserLoginForm

    def get_form_kwargs(self):
        # Adiciona o request aos kwargs do formulário
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """Método que é chamado quando o formulário é válido"""
        user = form.get_user()
        # Efetuar login manualmente para garantir que a sessão seja corretamente inicializada
        login(self.request, user)
        
        # Registrar o login no console para debug
        print(f"[LOGIN DEBUG] Usuário {user.email} autenticado com sucesso")
        print(f"[LOGIN DEBUG] Sessão: {self.request.session.session_key}")
        
        # Adicionar marcador de sessão para verificar no middleware
        self.request.session['authenticated_tenant'] = self.request.tenant.schema_name
        self.request.session.save()  # Forçar salvamento da sessão
        
        return HttpResponseRedirect(self.get_success_url())
    
    def post(self, request, *args, **kwargs):
        # Usa o método get_form_kwargs para garantir que o request seja passado
        form_kwargs = self.get_form_kwargs()
        form = self.form_class(**form_kwargs)
        
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        print(f"[DEBUG] ClienteUserLoginView: next_url={next_url}")
        
        if next_url:
            # Se for /home/, substituir pelo caminho correto
            if next_url == '/home/':
                return next_url  # Manter o caminho como está para evitar problemas de resolução
            return next_url
        
        default_url = reverse('LSCliente:clientehome')
        print(f"[DEBUG] Usando URL padrão: {default_url}")
        return default_url

class ClienteHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'cliente_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home"
        # Adicionar a lista de usuários ao contexto
        from LSCliente.models import UsuarioCliente
        context["usuarios"] = UsuarioCliente.objects.all().order_by('nome')
        context["tenant_name"] = self.request.tenant.nome
        context["tenant_schema"] = self.request.tenant.schema_name
        return context

class TenantPasswordResetView(PasswordResetView):
    """
    View para reset de senha que é consciente do tenant atual.
    """
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa o request para o formulário
        kwargs['request'] = self.request
        return kwargs

class TenantAwarePasswordResetConfirmView(View):
    """
    Uma versão completamente personalizada do PasswordResetConfirmView 
    que é consciente do sistema multi-tenant.
    """
    template_name = 'cliente_password_reset/password_reset_senha_nova_form.html'
    success_url = reverse_lazy('LSCliente:clientepassword_reset_complete')
    
    def get(self, request, *args, **kwargs):
        """
        Exibe o formulário de redefinição de senha e valida o token
        """
        # Debug
        print(f"[DEBUG] TenantAwarePasswordResetConfirmView GET chamado no tenant: {request.tenant.schema_name}")
        print(f"[DEBUG] uidb64: {kwargs.get('uidb64')}")
        print(f"[DEBUG] token: {kwargs.get('token')}")
        
        context = self._get_context_with_user(request, **kwargs)
        
        if context['validlink']:
            form = NewResetPasswordForm(user=context['user'])
            context['form'] = form
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """
        Processa o formulário de redefinição de senha
        """
        # Debug
        print(f"[DEBUG] TenantAwarePasswordResetConfirmView POST chamado no tenant: {request.tenant.schema_name}")
        
        context = self._get_context_with_user(request, **kwargs)
        
        if not context['validlink']:
            return render(request, self.template_name, context)
        
        form = NewResetPasswordForm(user=context['user'], data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Sua senha foi alterada com sucesso!")
            return redirect(self.success_url)
        
        context['form'] = form
        return render(request, self.template_name, context)
    
    def _get_context_with_user(self, request, **kwargs):
        """
        Método auxiliar para obter o contexto com informações do usuário e validação do token
        """
        context = {
            'validlink': False,
            'user': None,
            'tenant': request.tenant,
            'tenant_name': request.tenant.schema_name,
        }
        
        try:
            # Decodificar o uidb64
            uid = force_str(urlsafe_base64_decode(kwargs.get('uidb64', '')))
            print(f"[DEBUG] UID decodificado: {uid}")
            
            try:
                # Obtenha o usuário do tenant atual usando UsuarioCliente
                user = UsuarioCliente.objects.get(pk=uid)
                print(f"[DEBUG] Usuário encontrado: {user.email}")
                
                # Verificar o token
                token = kwargs.get('token', '')
                if default_token_generator.check_token(user, token):
                    context['validlink'] = True
                    context['user'] = user
                    print(f"[DEBUG] Token válido para usuário {user.email}")
                else:
                    print(f"[DEBUG] Token inválido para usuário {user.email}")
            except UsuarioCliente.DoesNotExist:
                print(f"[DEBUG] Usuário com ID {uid} não encontrado no tenant {request.tenant.schema_name}")
        except (TypeError, ValueError, OverflowError) as e:
            print(f"[DEBUG] Erro ao decodificar UID: {str(e)}")
        
        return context


class ClienteUserMangeView(LoginRequiredMixin, View):
    template_name = 'cliente_userManage.html'
    success_url = reverse_lazy('LSCliente:CLUserList')
    
    def get_object(self):
        user_id = self.request.GET.get('id')
        if user_id:
            return get_object_or_404(UsuarioCliente, id=user_id)
        return None
    
    def get(self, request, *args, **kwargs):
        usuario = self.get_object()
        form = UsuarioClienteForm(instance=usuario) if usuario else UsuarioClienteForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        usuario_id = request.POST.get('usuario_id')
        
        if usuario_id:
            # Modo de edição
            try:
                usuario = get_object_or_404(UsuarioCliente, id=usuario_id)
                form = UsuarioClienteForm(request.POST, request.FILES, instance=usuario)
            except Exception as e:
                messages.error(request, f'Usuário não encontrado. Erro: {str(e)}')
                return redirect(self.success_url)
        else:
            # Modo de criação
            form = UsuarioClienteForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Usuário salvo com sucesso!')
                return redirect(self.success_url)
            except Exception as e:
                messages.error(request, f'Erro ao salvar usuário: {str(e)}')
        
        # Se o formulário tem erros ou ocorreu uma exceção
        return render(request, self.template_name, {'form': form})

class ClienteUserListView(LoginRequiredMixin, ListView):
    model = UsuarioCliente
    template_name = 'cliente_userList.html'
    context_object_name = 'usuarios'
    paginate_by = 10  # Paginação de 10 usuários por página
    
    def get_queryset(self):
        queryset = UsuarioCliente.objects.all().order_by('-date_joined')
        
        # Filtro de pesquisa
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) | 
                Q(email__icontains=search_query)
            )
            
        return queryset

class ClienteUserToggleStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            usuario = get_object_or_404(UsuarioCliente, id=pk)
            usuario.is_active = not usuario.is_active
            usuario.save()
            
            if usuario.is_active:
                messages.success(request, f'Usuário {usuario.nome} ativado com sucesso!')
            else:
                messages.success(request, f'Usuário {usuario.nome} inativado com sucesso!')
                
        except Exception as e:
            messages.error(request, f'Erro ao alterar status do usuário: {str(e)}')
            
        return redirect('LSCliente:CLUserList')

class ClienteProvaCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'cliente_provaCreate.html'

class ClienteParametroView(LoginRequiredMixin, TemplateView):
    template_name = 'cliente_parametros.html'
    
    def get(self, request):
        # Obter ou criar configuração do cliente
        configuracao = ClienteSystemSettings.obter_configuracao()
        
        # Obter sessões ativas dos usuários - CORRIGIDO
        sessoes_ativas = []
        try:
            # Calcular tempo limite para sessões ativas
            tempo_limite = timezone.now() - timezone.timedelta(minutes=configuracao.tempo_maximo_inatividade)
            
            # Buscar sessões ativas usando o modelo correto
            from LSCliente.models import SessaoUsuarioCliente
            sessoes_query = SessaoUsuarioCliente.objects.select_related('usuario').filter(
                ultima_atividade__gte=tempo_limite
            ).order_by('-ultima_atividade')
            
            # Debug: Verificar se existem sessões
            print(f"Total de sessões encontradas: {sessoes_query.count()}")
            
            for sessao in sessoes_query:
                print(f"Sessão: {sessao.usuario.nome if hasattr(sessao.usuario, 'nome') else sessao.usuario.email}")
            
            sessoes_ativas = list(sessoes_query)
            
        except Exception as e:
            print(f"Erro ao buscar sessões ativas: {e}")
            sessoes_ativas = []
        
        # Total de usuários no sistema
        total_usuarios = UsuarioCliente.objects.filter(is_active=True).count()
        
        context = {
            'configuracao': configuracao,
            'sessoes_ativas': sessoes_ativas,
            'total_usuarios': total_usuarios,
            'title': 'Configurações do Sistema',
            # Debug info
            'debug_info': {
                'total_sessoes': len(sessoes_ativas),
                'tempo_limite': configuracao.tempo_maximo_inatividade,
            }
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        action = request.POST.get('action')
        configuracao = ClienteSystemSettings.obter_configuracao()
        
        try:
            if action == 'logout_user':
                user_id = request.POST.get('user_id')
                try:
                    user_id = int(user_id)
                    
                    # Buscar a sessão do usuário usando o modelo correto
                    from LSCliente.models import SessaoUsuarioCliente
                    sessao = SessaoUsuarioCliente.objects.filter(usuario_id=user_id).first()
                    
                    if sessao:
                        # Nome do usuário para a mensagem
                        usuario_nome = getattr(sessao.usuario, 'nome', None) or getattr(sessao.usuario, 'email', f'ID {user_id}')
                        
                        # Encerrar a sessão Django se existir
                        if hasattr(sessao, 'chave_sessao') and sessao.chave_sessao:
                            try:
                                from django.contrib.sessions.models import Session
                                Session.objects.filter(session_key=sessao.chave_sessao).delete()
                            except Exception as e:
                                print(f"Erro ao deletar sessão Django: {e}")
                        
                        # Remover do nosso rastreamento
                        sessao.delete()
                        
                        return JsonResponse({
                            'success': True, 
                            'message': f'Usuário {usuario_nome} deslogado com sucesso!'
                        })
                    else:
                        return JsonResponse({
                            'success': False, 
                            'message': 'Usuário não encontrado ou não está logado'
                        })
                        
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'message': 'ID de usuário inválido'})
            
            elif action == 'update_logo':
                # Debug: Verificar o que está chegando
                print(f"DEBUG - Action: {action}")
                print(f"DEBUG - request.FILES: {dict(request.FILES)}")
                print(f"DEBUG - request.POST: {dict(request.POST)}")
                print(f"DEBUG - FILES keys: {list(request.FILES.keys())}")
                
                # Processar upload da logo - verificar diferentes nomes de campo
                logo_file = None
                possible_names = ['logo', 'imagem_home_1', 'imagem', 'image', 'file', 'upload']
                
                for name in possible_names:
                    if name in request.FILES:
                        logo_file = request.FILES[name]
                        print(f"DEBUG - Arquivo encontrado com nome: {name}")
                        break
                
                if logo_file:
                    try:
                        # Verificar se é uma imagem válida
                        if not logo_file.content_type.startswith('image/'):
                            return JsonResponse({
                                'success': False, 
                                'message': f'Arquivo deve ser uma imagem. Tipo recebido: {logo_file.content_type}'
                            })
                        
                        # Salvar no campo correto (imagem_home_1 baseado no template)
                        configuracao.imagem_home_1 = logo_file
                        configuracao.save()
                        return JsonResponse({
                            'success': True, 
                            'message': 'Logo atualizada com sucesso!',
                            'logo_url': configuracao.imagem_home_1.url if configuracao.imagem_home_1 else None
                        })
                    except Exception as e:
                        print(f"Erro ao salvar logo: {e}")
                        return JsonResponse({
                            'success': False, 
                            'message': f'Erro ao salvar imagem: {str(e)}'
                        })
                else:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Nenhuma imagem foi enviada. Campos disponíveis: {list(request.FILES.keys())}'
                    })
            
            elif action == 'update_colors':
                # Atualizar cores do sistema
                try:
                    primary_color = request.POST.get('primary_color', '').strip()
                    second_color = request.POST.get('second_color', '').strip()
                    
                    if primary_color:
                        configuracao.system_primary_color = primary_color
                    if second_color:
                        configuracao.system_second_color = second_color
                    
                    configuracao.save()
                    
                    return JsonResponse({
                        'success': True, 
                        'message': 'Cores atualizadas com sucesso!'
                    })
                    
                except Exception as e:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Erro ao atualizar cores: {str(e)}'
                    })
            
            elif action == 'update_timeout':
                # Atualizar tempo de inatividade
                try:
                    timeout_minutes = int(request.POST.get('timeout_minutes', 0))
                    if timeout_minutes > 0:
                        configuracao.tempo_maximo_inatividade = timeout_minutes
                        configuracao.save()
                        
                        return JsonResponse({
                            'success': True, 
                            'message': f'Tempo de inatividade atualizado para {timeout_minutes} minutos!'
                        })
                    else:
                        return JsonResponse({
                            'success': False, 
                            'message': 'Tempo deve ser maior que 0'
                        })
                        
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False, 
                        'message': 'Tempo inválido fornecido'
                    })
            
            else:
                # Ação não reconhecida
                return JsonResponse({
                    'success': False, 
                    'message': 'Ação não reconhecida'
                })
            
        except Exception as e:
            print(f"Erro no processamento: {e}")
            return JsonResponse({
                'success': False, 
                'message': f'Erro interno do servidor: {str(e)}'
            })




def custom_logout_view(request):
    logout(request)
    return redirect('clientehome')


