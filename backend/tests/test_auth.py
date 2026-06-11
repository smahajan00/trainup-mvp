from __future__ import annotations


def test_register_success(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "  Taylor Morgan  ",
            "email": "  TAYLOR@example.com ",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["full_name"] == "Taylor Morgan"
    assert payload["user"]["email"] == "taylor@example.com"
    assert payload["user"]["has_profile"] is False
    assert "password_hash" not in payload["user"]


def test_duplicate_register_rejected(client) -> None:
    first_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Taylor Morgan",
            "email": "taylor@example.com",
            "password": "strongpass123",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Taylor Morgan",
            "email": "TAYLOR@example.com",
            "password": "strongpass123",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "An account with this email already exists."


def test_login_success(client) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Taylor Morgan",
            "email": "taylor@example.com",
            "password": "strongpass123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "  TAYLOR@example.com ",
            "password": "strongpass123",
        },
    )

    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "taylor@example.com"


def test_demo_credentials_login_is_allowed(client) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Subrata Mahajan",
            "email": " subrata@trainup.ai ",
            "password": "subrata123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "SUBRATA@TRAINUP.AI",
            "password": "subrata123",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "subrata@trainup.ai"


def test_non_demo_local_email_rejected(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Local User",
            "email": "local.user@trainup.local",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 422


def test_login_invalid_credentials_rejected(client) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Taylor Morgan",
            "email": "taylor@example.com",
            "password": "strongpass123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "taylor@example.com",
            "password": "wrongpass123",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password."


def test_auth_me_success(client) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Taylor Morgan",
            "email": "taylor@example.com",
            "password": "strongpass123",
        },
    )
    token = register_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["full_name"] == "Taylor Morgan"
    assert payload["email"] == "taylor@example.com"
    assert payload["has_profile"] is False
