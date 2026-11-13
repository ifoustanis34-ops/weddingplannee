import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_reports_ok_when_dependencies_are_up() -> None:
    response = APIClient().get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "cache": "ok"}


@pytest.mark.django_db
def test_health_reports_degraded_when_cache_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("core.views._check_cache", lambda: False)

    response = APIClient().get(reverse("health"))

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["cache"] == "error"
