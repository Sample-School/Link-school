from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,  # Adicionei para customização
)
from django.urls import reverse_lazy
from .forms import UserLoginForm
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class UserLoginView(LoginView):
    template_name = "registration/login.html"
    success_url = reverse_lazy('home')  # URL para redirecionar após login
    form_class = UserLoginForm

<<<<<<< HEAD
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
=======
    def get_context_data(self, **kwargs):
        """Adiciona contexto extra (opcional)"""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Login"  # Exemplo: pode ser usado no base.html
>>>>>>> 50f6e682909441418885a06bc40e62ccfea9d323
        return context

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            'page_title': "Dashboard"  # Título dinâmico
        })
        return context


class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"  # Seu template customizado
    email_template_name = 'LSDash/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')