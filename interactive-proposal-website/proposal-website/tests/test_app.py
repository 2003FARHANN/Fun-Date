import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path: Path):
    config_path = Path(__file__).resolve().parents[1] / "config.json"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "SITE_CONFIG_PATH": str(config_path),
        }
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def test_home_page_contains_exact_flow(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Will you go on a date with me?" in body
    assert "WAIT, YOU ACTUALLY SAID YES??" in body
    assert "What are we feeling?" in body
    assert "Glad you didn&#39;t say no." in body
    assert "one small fee" in body
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_fee_endpoint_returns_signed_fee(client):
    response = client.get("/api/fee")
    payload = response.get_json()

    assert response.status_code == 200
    assert isinstance(payload["amount"], int)
    assert payload["amount"] >= 0
    assert payload["symbol"] == "$"
    assert payload["token"]


def test_valid_response_is_saved(app, client):
    fee = client.get("/api/fee").get_json()
    future_date = (date.today() + timedelta(days=2)).isoformat()
    response = client.post(
        "/api/responses",
        json={
            "selected_date": future_date,
            "selected_time": "18:00",
            "food": "Pizza",
            "fee_amount": fee["amount"],
            "fee_token": fee["token"],
            "accepted": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["status"] == "saved"

    database = sqlite3.connect(app.config["DATABASE"])
    row = database.execute("SELECT selected_date, selected_time, food FROM responses").fetchone()
    database.close()
    assert row == (future_date, "18:00", "Pizza")


def test_tampered_fee_is_rejected(client):
    fee = client.get("/api/fee").get_json()
    response = client.post(
        "/api/responses",
        json={
            "selected_date": (date.today() + timedelta(days=1)).isoformat(),
            "selected_time": "18:00",
            "food": "Pizza",
            "fee_amount": fee["amount"] + 1,
            "fee_token": fee["token"],
            "accepted": True,
        },
    )
    assert response.status_code == 400
    assert "fee" in response.get_json()["error"].lower()


def test_past_date_is_rejected(client):
    fee = client.get("/api/fee").get_json()
    response = client.post(
        "/api/responses",
        json={
            "selected_date": (date.today() - timedelta(days=1)).isoformat(),
            "selected_time": "18:00",
            "food": "Pizza",
            "fee_amount": fee["amount"],
            "fee_token": fee["token"],
            "accepted": True,
        },
    )
    assert response.status_code == 400
    assert "future" in response.get_json()["error"].lower()


def test_config_is_valid_json():
    config_path = Path(__file__).resolve().parents[1] / "config.json"
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    assert config["fee"]["mode"] in {"random", "fixed"}
    assert len(config["food"]["options"]) >= 1
