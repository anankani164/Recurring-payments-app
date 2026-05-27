from datetime import date

from fastapi.testclient import TestClient

from app.main import app


def _superadmin_login(client: TestClient) -> str:
    login = client.post(
        "/auth/login",
        json={"username": "superadmin", "password": "Nankani1"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_protected_route_requires_token():
    client = TestClient(app)
    response = client.get("/clients")
    assert response.status_code == 401


def test_health_is_public():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_superadmin_can_create_user_and_run_end_to_end_flow():
    client = TestClient(app)
    token = _superadmin_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_user_response = client.post(
        "/users",
        headers=headers,
        json={
            "username": "admin2",
            "email": "admin2@example.com",
            "password": "Password123!",
            "role": "admin",
        },
    )
    assert create_user_response.status_code in (201, 409)

    create_client_response = client.post(
        "/clients",
        headers=headers,
        json={"name": "Client One", "email": "billing-client@example.com"},
    )
    assert create_client_response.status_code == 201
    created_client = create_client_response.json()

    create_project_response = client.post(
        "/projects",
        headers=headers,
        json={
            "name": "Project One",
            "client_id": created_client["id"],
            "amount_usd": 100.0,
            "recurrence": "monthly",
            "rate_type": "tts_selling",
            "next_invoice_date": "2026-05-01",
        },
    )
    assert create_project_response.status_code == 201
    created_project = create_project_response.json()

    create_rate_response = client.post(
        "/rates",
        headers=headers,
        json={
            "rate_date": "2026-05-01",
            "code": "USD",
            "cash_buying": 10.0,
            "cash_selling": 11.0,
            "tts_buying": 12.0,
            "tts_selling": 13.0,
            "source_url": "https://example.com/rates.pdf",
        },
    )
    assert create_rate_response.status_code in (201, 409)

    create_invoice_response = client.post(
        f"/projects/{created_project['id']}/invoice",
        headers=headers,
        params={"invoice_date": date(2026, 5, 1).isoformat()},
    )
    assert create_invoice_response.status_code in (200, 201)

    jobs_response = client.get("/jobs", headers=headers)
    assert jobs_response.status_code == 200
