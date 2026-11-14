"""Create (or promote) a Wedivo team account that opens the platform console and the admin.

    python manage.py create_platform_admin --email moi@exemple.com --name "Prénom Nom"

Without ``--password`` a temporary password is generated and printed once; it must be changed at
the first sign-in. An existing account keeps its password unless ``--password`` is given.
"""

from __future__ import annotations

import secrets
import string
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from accounts.models import User

ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0OoIl1")


def generate_password(length: int = 14) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


class Command(BaseCommand):
    help = "Crée ou promeut un compte super-administrateur (console plateforme et admin Django)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="", help="Nom complet (nouveau compte).")
        parser.add_argument("--password", default="", help="Sinon, mot de passe provisoire.")

    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"].strip().lower()
        password = options["password"]
        user = User.objects.filter(email__iexact=email).first()
        generated = False
        if user is None:
            if not options["name"].strip():
                raise CommandError("--name est obligatoire pour un nouveau compte.")
            if not password:
                password, generated = generate_password(), True
            user = User(email=email, full_name=" ".join(options["name"].split()))
        if password:
            try:
                validate_password(password, user)
            except ValidationError as exc:
                raise CommandError(" ".join(exc.messages)) from exc
            user.set_password(password)
            user.must_change_password = generated
        user.is_staff = user.is_superuser = True
        user.is_active = user.is_verified = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Super-administrateur prêt : {user.email}"))
        if generated:
            self.stdout.write(f"Mot de passe provisoire (à changer à la connexion) : {password}")
