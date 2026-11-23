"""Anti-bot (20/11/2026): honeypot, dated form token, real address, request limits."""

from __future__ import annotations

import time
from typing import Any
from unittest import mock

import pytest
from django.core.cache import caches
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from core import antibot
from core.audit import client_ip
from core.exceptions import BusinessError
from core.throttling import VisitorThrottle


@pytest.fixture
def guarded(settings: Any) -> None:
    settings.ANTIBOT_ENABLED = True
    settings.ANTIBOT_MIN_SECONDS = 2


def token(client: APIClient) -> str:
    response = client.get(reverse("auth-form-token"))
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    return str(response.json()["form_token"])


@pytest.mark.usefixtures("guarded")
def test_login_without_the_form_token_or_with_the_honeypot_is_refused(owner_a: User) -> None:
    client = APIClient()
    credentials = {"email": owner_a.email, "password": "wrong"}

    bare = client.post(reverse("auth-login"), credentials, format="json")
    trapped = client.post(
        reverse("auth-login"),
        {**credentials, "form_token": token(client), "website": "http://spam.example"},
        format="json",
    )
    forged = client.post(
        reverse("auth-login"), {**credentials, "form_token": "1:abc:def"}, format="json"
    )

    assert {bare.json()["code"], trapped.json()["code"], forged.json()["code"]} == {"bot_suspected"}


@pytest.mark.usefixtures("guarded")
def test_a_person_with_the_token_goes_through(owner_a: User) -> None:
    client = APIClient()

    response = client.post(
        reverse("auth-login"),
        {"email": owner_a.email, "password": "wrong", "form_token": token(client), "website": ""},
        format="json",
    )

    # Past the anti-bot: the password itself is checked.
    assert response.json()["code"] != "bot_suspected"


@pytest.mark.usefixtures("guarded")
def test_a_form_sent_faster_than_a_person_types_or_too_late_is_refused() -> None:
    issued = antibot.issue()
    with pytest.raises(BusinessError) as fast:
        antibot.check({"form_token": issued}, min_seconds=2)
    assert fast.value.error_code == "bot_suspected"

    three_hours_later = time.time() + 3 * 3600
    with (
        mock.patch("time.time", return_value=three_hours_later),
        pytest.raises(BusinessError),
    ):
        antibot.check({"form_token": issued})


def test_a_forged_forwarded_address_does_not_hide_the_visitor() -> None:
    factory = RequestFactory()
    spoofed = factory.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 41.202.219.70, 172.18.0.5")
    local = factory.get("/", HTTP_X_FORWARDED_FOR="172.18.0.1, 172.18.0.5")
    direct = factory.get("/", REMOTE_ADDR="41.202.219.71")

    assert client_ip(spoofed) == "41.202.219.70"
    assert client_ip(local) == "172.18.0.1"
    assert client_ip(direct) == "41.202.219.71"


def test_a_visitor_hammering_the_api_is_slowed_down(db: None) -> None:
    caches["default"].clear()
    with mock.patch.object(VisitorThrottle, "THROTTLE_RATES", {"anon": "3/min"}):
        client = APIClient()
        codes = [client.get(reverse("auth-form-token")).status_code for _ in range(5)]

    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]
