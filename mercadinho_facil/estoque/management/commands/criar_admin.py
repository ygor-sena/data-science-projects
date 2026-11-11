"""Cria o superusuário a partir de variáveis de ambiente, se ainda não existir.

Usado no deploy (Elastic Beanstalk), onde não há terminal interativo.
Variáveis: DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD,
DJANGO_SUPERUSER_EMAIL (opcional).
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o superusuário definido nas variáveis de ambiente (idempotente)."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD não definidos; nada a fazer.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Usuário '{username}' já existe.")
            return

        User.objects.create_superuser(
            username=username,
            email=os.getenv("DJANGO_SUPERUSER_EMAIL", ""),
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Superusuário '{username}' criado."))
