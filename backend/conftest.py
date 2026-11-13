"""Shared fixtures: two isolated organizations (A and B) with one member per role."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from django.conf import settings
from django.core.cache import caches
from rest_framework.test import APIClient

from accounts.models import Membership, User
from accounts.tokens import issue_tokens
from organizations.models import Organization
from tests.factories import MembershipFactory, OrganizationFactory, UserFactory


@pytest.fixture(autouse=True)
def _clear_caches() -> Iterator[None]:
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


@pytest.fixture
def org_a(db: None) -> Organization:
    return OrganizationFactory.create(slug="agence-a", name="Agence A")


@pytest.fixture
def org_b(db: None) -> Organization:
    return OrganizationFactory.create(slug="agence-b", name="Agence B")


@pytest.fixture
def make_member() -> Callable[..., User]:
    def _make(
        organization: Organization, role: str = Membership.Role.OWNER, **kwargs: object
    ) -> User:
        user = UserFactory.create(**kwargs)
        MembershipFactory.create(user=user, organization=organization, role=role)
        return user

    return _make


@pytest.fixture
def owner_a(org_a: Organization, make_member: Callable[..., User]) -> User:
    return make_member(org_a, Membership.Role.OWNER, email="owner@agence-a.ci")


@pytest.fixture
def owner_b(org_b: Organization, make_member: Callable[..., User]) -> User:
    return make_member(org_b, Membership.Role.OWNER, email="owner@agence-b.ci")


@pytest.fixture
def client_for() -> Callable[..., APIClient]:
    """API client authenticated by JWT cookie, targeting an organization via X-Organization."""

    def _client(user: User | None = None, organization: Organization | None = None) -> APIClient:
        client = APIClient()
        if user is not None:
            refresh = issue_tokens(user)
            client.cookies[settings.JWT_ACCESS_COOKIE] = str(refresh.access_token)
            client.cookies[settings.JWT_REFRESH_COOKIE] = str(refresh)
        if organization is not None:
            client.credentials(HTTP_X_ORGANIZATION=organization.slug)
        return client

    return _client
