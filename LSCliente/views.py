from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import TemplateView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.db import IntegrityError
from django.utils.text import slugify
from django import forms
from django.utils import timezone
from django.db.models import Q
from django.utils.decorators import method_decorator
import json
import logging

from .forms import CustomPasswordResetForm, UsuarioClienteForm, ClienteSystemSettingsForm, UserLoginForm, NewResetPasswordForm
from .models import Prova, QuestaoProva, UsuarioCliente, ClienteSystemSettings, SessaoUsuarioCliente
from .services.services import QuestaoService
from .services.dalle_service import *

logger = logging.getLogger(__name__)


class ClienteUserLoginView(LoginView):
    """View personalizada para login dos usuários cliente"""
    template_name = "clienteLogin.html"
    success_url = reverse_lazy('LSCliente:clientehome')
    form_class = UserLoginForm

    def get_form_kwargs(self):
        # Passa o request para o formulário para validações específicas do tenant
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """Processa login válido e configura sessão do tenant"""
        user = form.get_user()
        login(self.request, user)
        
        # Log para debug do processo de autenticação
        print(f"[LOGIN DEBUG] Usuário {user.email} autenticado com sucesso")
        print(f"[LOGIN DEBUG] Sessão: {self.request.session.session_key}")
        
        # Marca a sessão com o tenant atual para validação no middleware
        self.request.session['authenticated_tenant'] = self.request.tenant.schema_name
        self.request.session.save()
        
        return HttpResponseRedirect(self.get_success_url())
    
    def post(self, request, *args, **kwargs):
        # Garante que o formulário receba o request através do get_form_kwargs
        form_kwargs = self.get_form_kwargs()
        form = self.form_class(**form_kwargs)
        
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        """Define URL de redirecionamento após login bem-sucedido"""
        next_url = self.request.GET.get('next')
        print(f"[DEBUG] ClienteUserLoginView: next_url={next_url}")
        
        if next_url:
            # Mantém a URL original se for /home/ para não quebrar a resolução
            if next_url == '/home/':
                return next_url
            return next_url
        
        default_url = reverse('LSCliente:clientehome')
        print(f"[DEBUG] Usando URL padrão: {default_url}")
        return default_url


class ClienteHomeView(LoginRequiredMixin, TemplateView):
    """Dashboard principal do cliente"""
    template_name = 'cliente_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home"
        # Carrega lista de usuários para exibição no dashboard
        from LSCliente.models import UsuarioCliente
        context["usuarios"] = UsuarioCliente.objects.all().order_by('nome')
        context["tenant_name"] = self.request.tenant.nome
        context["tenant_schema"] = self.request.tenant.schema_name
        return context


class TenantPasswordResetView(PasswordResetView):
    """View para reset de senha que funciona com multi-tenant"""
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Importante: passa o request para o formulário conseguir filtrar por tenant
        kwargs['request'] = self.request
        return kwargs


class TenantAwarePasswordResetConfirmView(View):
    """
    View personalizada para confirmar reset de senha no ambiente multi-tenant.
    Substitui a view padrão do Django que não funciona bem com tenants.
    """
    template_name = 'cliente_password_reset/password_reset_senha_nova_form.html'
    success_url = reverse_lazy('LSCliente:clientepassword_reset_complete')
    
    def get(self, request, *args, **kwargs):
        """Exibe formulário de nova senha após validar token"""
        print(f"[DEBUG] Reset de senha GET no tenant: {request.tenant.schema_name}")
        print(f"[DEBUG] uidb64: {kwargs.get('uidb64')}")
        print(f"[DEBUG] token: {kwargs.get('token')}")
        
        context = self._get_context_with_user(request, **kwargs)
        
        if context['validlink']:
            form = NewResetPasswordForm(user=context['user'])
            context['form'] = form
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """Processa nova senha"""
        print(f"[DEBUG] Reset de senha POST no tenant: {request.tenant.schema_name}")
        
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
        """Valida token e retorna contexto com informações do usuário"""
        context = {
            'validlink': False,
            'user': None,
            'tenant': request.tenant,
            'tenant_name': request.tenant.schema_name,
        }
        
        try:
            # Decodifica o UID que vem na URL
            uid = force_str(urlsafe_base64_decode(kwargs.get('uidb64', '')))
            print(f"[DEBUG] UID decodificado: {uid}")
            
            try:
                # Busca usuário no tenant atual
                user = UsuarioCliente.objects.get(pk=uid)
                print(f"[DEBUG] Usuário encontrado: {user.email}")
                
                # Verifica se o token ainda é válido
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
    """Gerenciamento de usuários - criação e edição"""
    template_name = 'cliente_userManage.html'
    success_url = reverse_lazy('LSCliente:CLUserList')
    
    def get_object(self):
        """Retorna usuário para edição baseado no ID da query string"""
        user_id = self.request.GET.get('id')
        if user_id:
            return get_object_or_404(UsuarioCliente, id=user_id)
        return None
    
    def get(self, request, *args, **kwargs):
        """Exibe formulário vazio ou preenchido para edição"""
        usuario = self.get_object()
        form = UsuarioClienteForm(instance=usuario) if usuario else UsuarioClienteForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        """Processa criação ou edição de usuário"""
        usuario_id = request.POST.get('usuario_id')
        
        if usuario_id:
            # Modo edição - carrega usuário existente
            try:
                usuario = get_object_or_404(UsuarioCliente, id=usuario_id)
                form = UsuarioClienteForm(request.POST, request.FILES, instance=usuario)
            except Exception as e:
                messages.error(request, f'Usuário não encontrado. Erro: {str(e)}')
                return redirect(self.success_url)
        else:
            # Modo criação - novo usuário
            form = UsuarioClienteForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Usuário salvo com sucesso!')
                return redirect(self.success_url)
            except Exception as e:
                messages.error(request, f'Erro ao salvar usuário: {str(e)}')
        
        # Se chegou aqui, tem erro no formulário
        return render(request, self.template_name, {'form': form})


class ClienteUserListView(LoginRequiredMixin, ListView):
    """Lista paginada de usuários com busca"""
    model = UsuarioCliente
    template_name = 'cliente_userList.html'
    context_object_name = 'usuarios'
    paginate_by = 10
    
    def get_queryset(self):
        """Aplica filtros de busca e ordenação"""
        queryset = UsuarioCliente.objects.all().order_by('-date_joined')
        
        # Filtro de busca por nome ou email
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) | 
                Q(email__icontains=search_query)
            )
            
        return queryset


class ClienteUserToggleStatusView(LoginRequiredMixin, View):
    """Ativa/desativa usuários via AJAX"""
    
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


@method_decorator(login_required, name='dispatch')
class ClienteProvaCreateView(LoginRequiredMixin, View):
    """View principal para criação de provas com IA"""
    template_name = 'cliente_provaCreate.html' 

    def get(self, request):
        """Carrega tela de criação com questões disponíveis"""
        questoes_dashboard = QuestaoService.buscar_questoes_dashboard()
        config_cliente = ClienteSystemSettings.obter_configuracao()
        
        context = {
            'questoes_dashboard': questoes_dashboard,
            'tipos_prova': Prova.TIPO_PROVA_CHOICES,
            'config_cliente': config_cliente,
            'dalle_disponivel': bool(settings.OPENAI_API_KEY),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Roteador para diferentes ações da criação de prova"""
        action = request.POST.get('action')
        
        if action == 'salvar_prova':
            return self._salvar_prova(request)
        elif action == 'gerar_imagem_questao':
            return self._gerar_imagem_questao(request)
        elif action == 'gerar_todas_imagens':
            return self._gerar_todas_imagens_prova(request)
        elif action == 'buscar_questao':
            return self._buscar_questao_ajax(request)
        elif action == 'criar_questao':
            return self._criar_nova_questao(request)
        
        return JsonResponse({'error': 'Ação não reconhecida'}, status=400)
    
    def _salvar_prova(self, request):
        """Salva prova no banco e opcionalmente gera imagens automaticamente"""
        try:
            # Extrai dados do formulário
            titulo = request.POST.get('titulo')
            materia = request.POST.get('materia')
            tipo_prova = request.POST.get('tipo_prova')
            acessibilidade_prova = request.POST.get('acessibilidade_prova', 1)
            questoes_selecionadas = json.loads(request.POST.get('questoes_selecionadas', '[]'))
            gerar_imagens_automatico = request.POST.get('gerar_imagens_automatico', 'false') == 'true'
            
            # Validações básicas
            if not titulo or not materia or not tipo_prova:
                return JsonResponse({'error': 'Todos os campos são obrigatórios'}, status=400)
            
            if not questoes_selecionadas:
                return JsonResponse({'error': 'Adicione pelo menos uma questão'}, status=400)
            
            # Cria a prova principal
            prova = Prova.objects.create(
                titulo=titulo,
                materia=materia,
                tipo_prova=tipo_prova,
                acessibilidade_prova=int(acessibilidade_prova),
                criado_por=request.user
            )
            
            # Lista para controlar questões que precisam de imagem
            questoes_para_gerar_imagem = []
            
            # Adiciona cada questão à prova
            for i, questao_data in enumerate(questoes_selecionadas, 1):
                questao_completa = QuestaoService.buscar_questao_completa(questao_data['id'])
                acessibilidade_questao = questao_data.get('acessibilidade', 1)
                
                questao_prova = QuestaoProva.objects.create(
                    prova=prova,
                    questao_id=questao_data['id'],
                    questao_dados=questao_completa,
                    ordem=i,
                    acessibilidade_questao=int(acessibilidade_questao),
                    fonte_imagem='dalle' if acessibilidade_questao == 3 else 'estatica'
                )
                
                # Se precisa de imagem (acessibilidade nível 3), adiciona na lista
                if acessibilidade_questao == 3:
                    questoes_para_gerar_imagem.append({
                        'questao_prova_id': questao_prova.id,
                        'questao_data': questao_completa
                    })
            
            response_data = {
                'success': True, 
                'prova_id': prova.id,
                'questoes_com_imagem': len(questoes_para_gerar_imagem)
            }
            
            # Gerar imagens automaticamente se foi solicitado
            if gerar_imagens_automatico and questoes_para_gerar_imagem:
                try:
                    imagens_geradas = self._processar_geracao_imagens(questoes_para_gerar_imagem)
                    response_data['imagens_geradas'] = imagens_geradas
                    
                    # Atualiza status da prova
                    if imagens_geradas > 0:
                        prova.imagens_geradas = True
                        prova.data_geracao_imagens = timezone.now()
                        prova.save()
                        
                except Exception as e:
                    logger.error(f"Erro ao gerar imagens: {str(e)}")
                    response_data['warning'] = 'Prova salva, mas algumas imagens não puderam ser geradas'
            
            messages.success(request, 'Prova salva com sucesso!')
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Dados das questões inválidos'}, status=400)
        except Exception as e:
            logger.error(f"Erro ao salvar prova: {str(e)}")
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)
    
    def _gerar_imagem_questao(self, request):
        """Gera imagem para uma questão específica usando DALL-E"""
        try:
            questao_prova_id = request.POST.get('questao_prova_id')
            if not questao_prova_id:
                return JsonResponse({'error': 'ID da questão não fornecido'}, status=400)
            
            questao_prova = QuestaoProva.objects.get(id=questao_prova_id)
            
            # Usa o serviço DALL-E para gerar a imagem
            imagem_path = dalle_service.gerar_imagem_questao(questao_prova.questao_dados)
            
            if imagem_path:
                # Salva o caminho da imagem no banco
                questao_prova.imagem_gerada = imagem_path
                questao_prova.data_geracao_imagem = timezone.now()
                questao_prova.save()
                
                return JsonResponse({
                    'success': True,
                    'imagem_url': questao_prova.get_imagem_url(),
                    'message': 'Imagem gerada com sucesso!'
                })
            else:
                return JsonResponse({'error': 'Falha ao gerar imagem'}, status=500)
                
        except QuestaoProva.DoesNotExist:
            return JsonResponse({'error': 'Questão não encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {str(e)}")
            return JsonResponse({'error': f'Erro ao gerar imagem: {str(e)}'}, status=500)
    
    def _gerar_todas_imagens_prova(self, request):
        """Gera todas as imagens necessárias para uma prova de uma vez"""
        try:
            prova_id = request.POST.get('prova_id')
            if not prova_id:
                return JsonResponse({'error': 'ID da prova não fornecido'}, status=400)
            
            prova = Prova.objects.get(id=prova_id, criado_por=request.user)
            questoes_com_imagem = prova.get_questoes_com_imagem().filter(imagem_gerada__isnull=True)
            
            if not questoes_com_imagem.exists():
                return JsonResponse({'message': 'Todas as imagens já foram geradas!'})
            
            # Prepara dados para geração em lote
            questoes_para_gerar = [
                {
                    'questao_prova_id': q.id,
                    'questao_data': q.questao_dados
                }
                for q in questoes_com_imagem
            ]
            
            # Processa geração das imagens
            imagens_geradas = self._processar_geracao_imagens(questoes_para_gerar)
            
            # Atualiza status da prova se necessário
            if imagens_geradas > 0:
                prova.imagens_geradas = prova.todas_imagens_geradas()
                if prova.imagens_geradas:
                    prova.data_geracao_imagens = timezone.now()
                prova.save()
            
            return JsonResponse({
                'success': True,
                'imagens_geradas': imagens_geradas,
                'total_questoes': len(questoes_para_gerar),
                'message': f'{imagens_geradas} imagens geradas com sucesso!'
            })
            
        except Prova.DoesNotExist:
            return JsonResponse({'error': 'Prova não encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Erro ao gerar imagens da prova: {str(e)}")
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)
    
    def _processar_geracao_imagens(self, questoes_para_gerar):
        """Processa a geração de imagens para múltiplas questões sequencialmente"""
        imagens_geradas = 0
        
        for questao_info in questoes_para_gerar:
            try:
                questao_prova = QuestaoProva.objects.get(id=questao_info['questao_prova_id'])
                
                # Tenta gerar imagem via DALL-E
                imagem_path = dalle_service.gerar_imagem_questao(questao_info['questao_data'])
                
                if imagem_path:
                    questao_prova.imagem_gerada = imagem_path
                    questao_prova.data_geracao_imagem = timezone.now()
                    questao_prova.save()
                    imagens_geradas += 1
                    logger.info(f"Imagem gerada para questão {questao_prova.id}")
                else:
                    logger.warning(f"Falha ao gerar imagem para questão {questao_prova.id}")
                    
            except Exception as e:
                logger.error(f"Erro ao processar questão {questao_info['questao_prova_id']}: {str(e)}")
                continue
        
        return imagens_geradas

    def _buscar_questao_ajax(self, request):
        """Busca dados completos de uma questão via AJAX"""
        try:
            questao_id = request.POST.get('questao_id')
            if not questao_id:
                return JsonResponse({'error': 'ID da questão não fornecido'}, status=400)
            
            questao = QuestaoService.buscar_questao_completa(questao_id)
            
            if questao:
                return JsonResponse({'success': True, 'questao': questao})
            else:
                return JsonResponse({'error': 'Questão não encontrada'}, status=404)
        
        except Exception as e:
            return JsonResponse({'error': f'Erro ao buscar questão: {str(e)}'}, status=500)
    
    def _criar_nova_questao(self, request):
        """Placeholder para criação de novas questões"""
        try:
            # TODO: Implementar funcionalidade de criação de questões
            return JsonResponse({'success': True, 'message': 'Funcionalidade em desenvolvimento'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ClienteParametroView(LoginRequiredMixin, TemplateView):
    """Configurações do sistema e monitoramento de sessões"""
    template_name = 'cliente_parametros.html'
    
    def get(self, request):
        """Carrega página de configurações com sessões ativas"""
        # Obtém configuração atual do cliente
        configuracao = ClienteSystemSettings.obter_configuracao()
        
        # Busca sessões ativas baseado no tempo de inatividade
        sessoes_ativas = []
        try:
            # Calcula tempo limite para considerar sessão ativa
            tempo_limite = timezone.now() - timezone.timedelta(minutes=configuracao.tempo_maximo_inatividade)
            
            # Busca sessões que ainda estão dentro do tempo limite
            from LSCliente.models import SessaoUsuarioCliente
            sessoes_query = SessaoUsuarioCliente.objects.select_related('usuario').filter(
                ultima_atividade__gte=tempo_limite
            ).order_by('-ultima_atividade')
            
            # Debug: mostra quantas sessões foram encontradas
            print(f"Total de sessões encontradas: {sessoes_query.count()}")
            
            for sessao in sessoes_query:
                print(f"Sessão: {sessao.usuario.nome if hasattr(sessao.usuario, 'nome') else sessao.usuario.email}")
            
            sessoes_ativas = list(sessoes_query)
            
        except Exception as e:
            print(f"Erro ao buscar sessões ativas: {e}")
            sessoes_ativas = []
        
        # Conta total de usuários ativos no sistema
        total_usuarios = UsuarioCliente.objects.filter(is_active=True).count()
        
        context = {
            'configuracao': configuracao,
            'sessoes_ativas': sessoes_ativas,
            'total_usuarios': total_usuarios,
            'title': 'Configurações do Sistema',
            # Info para debug se necessário
            'debug_info': {
                'total_sessoes': len(sessoes_ativas),
                'tempo_limite': configuracao.tempo_maximo_inatividade,
            }
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Processa diferentes ações de configuração via AJAX"""
        action = request.POST.get('action')
        configuracao = ClienteSystemSettings.obter_configuracao()
        
        try:
            if action == 'logout_user':
                # Força logout de um usuário específico
                user_id = request.POST.get('user_id')
                try:
                    user_id = int(user_id)
                    
                    # Busca sessão do usuário no nosso controle
                    from LSCliente.models import SessaoUsuarioCliente
                    sessao = SessaoUsuarioCliente.objects.filter(usuario_id=user_id).first()
                    
                    if sessao:
                        # Nome do usuário para mostrar na mensagem
                        usuario_nome = getattr(sessao.usuario, 'nome', None) or getattr(sessao.usuario, 'email', f'ID {user_id}')
                        
                        # Remove sessão do Django se existir
                        if hasattr(sessao, 'chave_sessao') and sessao.chave_sessao:
                            try:
                                from django.contrib.sessions.models import Session
                                Session.objects.filter(session_key=sessao.chave_sessao).delete()
                            except Exception as e:
                                print(f"Erro ao deletar sessão Django: {e}")
                        
                        # Remove do nosso rastreamento
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
                # Atualiza logo do sistema
                print(f"DEBUG - Action: {action}")
                print(f"DEBUG - request.FILES: {dict(request.FILES)}")
                print(f"DEBUG - request.POST: {dict(request.POST)}")
                print(f"DEBUG - FILES keys: {list(request.FILES.keys())}")
                
                # Verifica diferentes nomes possíveis para o campo de arquivo
                logo_file = None
                possible_names = ['logo', 'imagem_home_1', 'imagem', 'image', 'file', 'upload']
                
                for name in possible_names:
                    if name in request.FILES:
                        logo_file = request.FILES[name]
                        print(f"DEBUG - Arquivo encontrado com nome: {name}")
                        break
                
                if logo_file:
                    try:
                        # Verifica se realmente é uma imagem
                        if not logo_file.content_type.startswith('image/'):
                            return JsonResponse({
                                'success': False, 
                                'message': f'Arquivo deve ser uma imagem. Tipo recebido: {logo_file.content_type}'
                            })
                        
                        # Salva no campo correto baseado no template
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
                # Atualiza cores do tema do sistema
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
