from __future__ import annotations

import re
from typing import Any

import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services import make_email_token
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_verify_email_marks_user_verified() -> None:
    user = UserFactory.create(is_verified=False)

    response = APIClient().post(
        reverse("auth-verify-email"), {"token": make_email_token(user)}, format="json"
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.is_verified


def test_verify_email_rejects_tampered_token() -> None:
    response = APIClient().post(reverse("auth-verify-email"), {"token": "faux"}, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_token"


def test_password_reset_flow(django_capture_on_commit_callbacks: Any) -> None:
    user = UserFactory.create(email="mariam@agence.ci")

    with django_capture_on_commit_callbacks(execute=True):
        response = APIClient().post(
            reverse("auth-password-reset"), {"email": "Mariam@Agence.ci"}, format="json"
        )
    assert response.status_code == 204
    assert len(mail.outbox) == 1
    match = re.search(r"uid=([\w-]+)&token=([\w-]+)", str(mail.outbox[0].body))
    assert match is not None

    confirm = APIClient().post(
        reverse("auth-password-reset-confirm"),
        {"uid": match.group(1), "token": match.group(2), "password": "Nouveau-mot-2026!"},
        format="json",
    )
    assert confirm.status_code == 204
    user.refresh_from_db()
    assert user.check_password("Nouveau-mot-2026!")

    reused = APIClient().post(
        reverse("auth-password-reset-confirm"),
        {"uid": match.group(1), "token": match.group(2), "password": "Encore-autre-2026!"},
        format="json",
    )
    assert reused.json()["code"] == "invalid_token"


def test_password_reset_does_not_reveal_unknown_emails(
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = APIClient().post(
            reverse("auth-password-reset"), {"email": "inconnu@nulle-part.ci"}, format="json"
        )

    assert response.status_code == 204
    assert mail.outbox == []
    assert not User.objects.filter(email="inconnu@nulle-part.ci").exists()
