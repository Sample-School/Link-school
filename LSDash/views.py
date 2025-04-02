from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import UserLoginForm
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.contrib.auth import login, logout, authenticate
from django.http import HttpResponseRedirect
from django.shortcuts import render


# Imports  local
from .forms import UserLoginForm

class UserLoginView(auth_views.LoginView):
    template_name = "login.html"
    success_url = reverse_lazy('home')
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

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'