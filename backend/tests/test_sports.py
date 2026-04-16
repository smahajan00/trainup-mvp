from __future__ import annotations


def test_authenticated_user_can_fetch_sports(client) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Jordan Carter",
            "email": "jordan@example.com",
            "password": "strongpass123",
        },
    )
    token = register_response.json()["access_token"]

    response = client.get(
        "/api/sports",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert all(set(sport.keys()) == {"id", "sport_name"} for sport in payload)
    assert all(isinstance(sport["id"], str) and sport["id"] for sport in payload)
    assert [sport["sport_name"] for sport in payload] == [
        "Basketball",
        "Football",
        "Gym",
    ]
