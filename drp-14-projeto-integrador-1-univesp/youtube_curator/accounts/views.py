from django import forms
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from curator.services.modules import seed_user_modules


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, label="Nome")
    last_name = forms.CharField(max_length=50, required=False, label="Sobrenome")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "password1", "password2")


def register(request):
    if request.user.is_authenticated:
        return redirect("curator:dashboard")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            seed_user_modules(user)
            login(request, user)
            return redirect("curator:dashboard")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})
