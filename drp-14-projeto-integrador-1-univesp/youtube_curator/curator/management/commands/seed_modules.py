from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from curator.services.modules import DEFAULT_MODULES, seed_user_modules


class Command(BaseCommand):
    help = "Cria os 3 módulos de treinamento padrão para um usuário"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help="Username do usuário que receberá os módulos",
        )

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuário '{username}' não encontrado.")

        created = 0
        for data in DEFAULT_MODULES:
            from curator.models import TrainingModule

            _, was_created = TrainingModule.objects.get_or_create(
                slug=data["slug"],
                created_by=user,
                defaults=data,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  Criado: {data['name']}"))
            else:
                self.stdout.write(f"  Já existe: {data['name']}")

        self.stdout.write(self.style.SUCCESS(f"\n{created} módulo(s) criado(s) para {username}."))
