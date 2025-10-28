from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Crea un superusuario por defecto (admin/admin) si no existe'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@keepa-ia.com'
        password = 'admin'

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'El usuario "{username}" ya existe.')
            )
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superusuario "{username}" creado exitosamente con contraseña "{password}"'
                )
            )
