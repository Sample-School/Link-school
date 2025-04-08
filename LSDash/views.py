from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .forms import UserLoginForm


# View de login personalizada baseada em classe
class UserLoginView(LoginView):
    template_name = "login.html"  # Template a ser usado
    success_url = reverse_lazy('home')  # Para onde redirecionar após login com sucesso
    form_class = UserLoginForm  # Formulário de login personalizado

    def post(self, request, *args, **kwargs):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            # Django chama o campo de "username" no form, mesmo que seja um email
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Autentica o usuário com base no email (caso seu AUTH_USER_MODEL use email como USERNAME_FIELD)
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect(self.get_success_url())  # Redireciona após login
                else:
                    form.add_error(None, "Esta conta está inativa.")
            else:
                form.add_error(None, "Email ou senha incorretos.")
        return self.form_invalid(form)

    def get_success_url(self):
        return self.success_url

    def get_context_data(self, **kwargs):
        # Adiciona variável de contexto ao template
        context = super().get_context_data(**kwargs)
        context["title"] = "Login"
        return context


# Página protegida por login
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Home"
        return context


# View baseada em classe para iniciar o processo de recuperação de senha
class PasswordResetView(FormView):
    template_name = "password_reset_form.html"
    form_class = PasswordResetForm
    success_url = reverse_lazy("password_reset_done")  # Redirecionamento após envio bem-sucedido

    def form_valid(self, form):
        # Captura o e-mail enviado no formulário
        email = form.cleaned_data["email"]
        users = get_user_model().objects.filter(email=email)

        if users.exists():
            for user in users:
                # Geração de token único para o usuário
                token = default_token_generator.make_token(user)
                # Codifica o ID do usuário
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                # Cria URL de redefinição
                reset_url = self.request.build_absolute_uri(f"/recuperar/{uid}/{token}/")

                # Renderiza o corpo do e-mail a partir de template
                message = render_to_string("password_reset_email.html", {
                    "user": user,
                    "reset_url": reset_url,
                })

                # Envia e-mail
                send_mail(
                    "Recuperação de Senha",
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )

            # Mensagem de feedback ao usuário
            messages.success(self.request, "Um e-mail foi enviado com instruções para recuperar sua senha.")
        else:
            # Mesmo que não encontre, damos feedback neutro para segurança
            messages.info(self.request, "Se este e-mail estiver cadastrado, você receberá instruções em breve.")

        return super().form_valid(form)


# View baseada em classe para confirmar o link de redefinição e alterar a senha
class PasswordResetConfirmView(View):
    template_name = "password_reset_confirm.html"

    def get_user(self, uidb64):
        try:
            # Decodifica o UID enviado na URL
            uid = force_str(urlsafe_base64_decode(uidb64))
            return get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return None

    # Exibe o formulário de nova senha
    def get(self, request, uidb64, token):
        user = self.get_user(uidb64)
        if user and default_token_generator.check_token(user, token):
            form = SetPasswordForm(user)
            return render(request, self.template_name, {"form": form})
        else:
            messages.error(request, "O link de recuperação está inválido ou expirado.")
            return redirect("password_reset")

    # Processa o envio do novo formulário de senha
    def post(self, request, uidb64, token):
        user = self.get_user(uidb64)
        if user and default_token_generator.check_token(user, token):
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()  # Salva nova senha
                login(request, user)  # Loga o usuário automaticamente
                messages.success(request, "Sua senha foi alterada com sucesso!")
                return redirect("password_reset_complete")
            return render(request, self.template_name, {"form": form})
        else:
            messages.error(request, "O link de recuperação está inválido ou expirado.")
            return redirect("password_reset")
