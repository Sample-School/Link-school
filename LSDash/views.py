from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy,  reverse
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

#Imports Locais
from .forms import UserLoginForm, CollabManageForm
from .models import UserModel


class UserLoginView(LoginView):
    template_name = "login.html"
    success_url = reverse_lazy('home')  # URL para redirecionar após login
    form_class = UserLoginForm

    def post(self, request, *args, **kwargs):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # Aqui o campo é username, mas contém o email
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)  # Django usa o USERNAME_FIELD aqui

            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(self.get_success_url())
                else:
                    form.add_error(None, "Esta conta está inativa.")
            else:
                form.add_error(None, "Email ou senha incorretos.")

        return render(request, self.template_name, {'form': form})

    def get_success_url(self):
        return self.success_url
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Login"
        return context
    
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home"
        return context


class CollabManage(LoginRequiredMixin,  TemplateView):
    template_name = 'CollabManage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.GET.get('user_id') or kwargs.get('user_id')
        logged_user = self.request.user

        if user_id:
            try:
                selected_user = UserModel.objects.get(user_id=user_id)
                context['selected_user'] = selected_user  # Mudado de 'user' para 'selected_user'
                context['form'] = CollabManageForm(instance=selected_user)
                context['user_id'] = user_id
                context['tipo_usuario_display'] = (
                    'Administrador' if selected_user.is_staff and selected_user.is_superuser else 'Colaborador'
                )
                context['status_usuario_display'] = (
                    'Ativo' if selected_user.is_active else 'Inativo'
                )
            except UserModel.DoesNotExist:
                context['error_message'] = f"Usuário com ID {user_id} não encontrado."
                context['form'] = CollabManageForm()
        else:
            context['form'] = CollabManageForm()

        
        
        context['users'] = UserModel.objects.all()
        context['logged_user'] = logged_user  # Adicionando o usuário logado ao contexto

        return context

    def post(self, request, *args, **kwargs):
        user_id = request.GET.get('user_id') or kwargs.get('user_id')

        if user_id:
            try:
                selected_user = UserModel.objects.get(user_id=user_id)  # Mudado de user para selected_user
                old_password = selected_user.password
                
                form = CollabManageForm(request.POST, instance=selected_user)
                
                if form.is_valid():
                    updated_user = form.save(commit=False)
                    updated_user.password = old_password
                    updated_user.save()
                    form.save_m2m()
                    
                    messages.success(request, "Usuário atualizado com sucesso!", extra_tags="user_edit")
                    return redirect(f"{reverse('AT-A-EU-001')}?user_id={user_id}")
                else:
                    messages.error(request, "Erro no formulário. Por favor, verifique os campos." , extra_tags="user_edit")
                    return self.render_to_response(self.get_context_data(form=form, selected_user=selected_user))
            except UserModel.DoesNotExist:
                messages.error(request, f"Usuário com ID {user_id} não encontrado.", extra_tags="user_edit")
                return self.render_to_response(self.get_context_data())
        else:
            messages.error(request, "Usuário não encontrado.", extra_tags="user_edit")
            return self.render_to_response(self.get_context_data())