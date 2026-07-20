from __future__ import annotations

import json
import os
import secrets
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import click
from flask import Flask, current_app, g, jsonify, render_template, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"


def load_site_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    required_sections = {"site", "proposal", "schedule", "food", "confirmation", "fee", "finale", "theme"}
    missing = sorted(required_sections.difference(config))
    if missing:
        raise RuntimeError(f"Missing config sections: {', '.join(missing)}")
    return config


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
        DATABASE=os.environ.get("DATABASE_PATH", str(Path(app.instance_path) / "proposal.sqlite3")),
        SITE_CONFIG_PATH=os.environ.get("SITE_CONFIG_PATH", str(DEFAULT_CONFIG_PATH)),
        MAX_CONTENT_LENGTH=32 * 1024,
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.extensions["site_config"] = load_site_config(Path(app.config["SITE_CONFIG_PATH"]))

    register_database(app)
    register_routes(app)
    register_security_headers(app)
    register_cli(app)

    with app.app_context():
        init_database()

    return app


def get_database() -> sqlite3.Connection:
    if "database" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        g.database = sqlite3.connect(database_path)
        g.database.row_factory = sqlite3.Row
    return g.database


def close_database(_error: BaseException | None = None) -> None:
    database = g.pop("database", None)
    if database is not None:
        database.close()


def init_database() -> None:
    database = get_database()
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS responses (
            id TEXT PRIMARY KEY,
            selected_date TEXT NOT NULL,
            selected_time TEXT NOT NULL,
            food TEXT NOT NULL,
            fee_amount INTEGER NOT NULL,
            fee_currency TEXT NOT NULL,
            accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
            created_at TEXT NOT NULL
        )
        """
    )
    database.commit()


def register_database(app: Flask) -> None:
    app.teardown_appcontext(close_database)


def public_config() -> dict[str, Any]:
    config = current_app.extensions["site_config"]
    safe_config = dict(config)
    safe_config["fee"] = {
        "title": config["fee"]["title"],
        "description": config["fee"]["description"],
        "plan_name": config["fee"]["plan_name"],
        "fine_print": config["fee"]["fine_print"],
        "button_template": config["fee"]["button_template"],
        "currency_symbol": config["fee"]["currency_symbol"],
    }
    return safe_config


def generate_fee(config: dict[str, Any]) -> int:
    fee = config["fee"]
    if fee.get("mode", "random").lower() == "fixed":
        return max(0, int(fee.get("fixed_amount", 499)))

    minimum = max(0, int(fee.get("random_min", 99)))
    maximum = max(minimum, int(fee.get("random_max", 999)))
    step = max(1, int(fee.get("random_step", 10)))
    choices = list(range(minimum, maximum + 1, step))
    if not choices:
        return minimum
    return secrets.choice(choices)


def validate_response(payload: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    required = ("selected_date", "selected_time", "food", "fee_amount", "accepted")
    if any(field not in payload for field in required):
        return None, "Some required details are missing."

    try:
        selected_date = date.fromisoformat(str(payload["selected_date"]))
    except ValueError:
        return None, "Please choose a valid date."

    if selected_date < date.today():
        return None, "Please choose today or a future date."

    selected_time = str(payload["selected_time"])
    valid_times = {item["value"] for item in config["schedule"]["time_options"]}
    if selected_time not in valid_times:
        return None, "Please choose an available time."

    food = str(payload["food"])
    valid_foods = {item["name"] for item in config["food"]["options"]}
    if food not in valid_foods:
        return None, "Please choose one of the food options."

    try:
        fee_amount = max(0, int(payload["fee_amount"]))
    except (TypeError, ValueError):
        return None, "The playful fee is invalid."

    if payload["accepted"] is not True:
        return None, "Confirmation is required."

    return {
        "selected_date": selected_date.isoformat(),
        "selected_time": selected_time,
        "food": food[:80],
        "fee_amount": fee_amount,
        "accepted": 1,
    }, None


def register_routes(app: Flask) -> None:
    @app.before_request
    def create_csp_nonce():
        g.csp_nonce = secrets.token_urlsafe(18)

    @app.get("/")
    def index():
        return render_template("index.html", site_config=public_config(), csp_nonce=g.csp_nonce)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/fee")
    def fee():
        config = current_app.extensions["site_config"]
        amount = generate_fee(config)
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="proposal-fee")
        return jsonify(
            amount=amount,
            currency=config["fee"].get("currency", "USD"),
            symbol=config["fee"].get("currency_symbol", "$"),
            token=serializer.dumps({"amount": amount}),
        )

    @app.post("/api/responses")
    def save_response():
        if not request.is_json:
            return jsonify(error="JSON request required."), 415

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Invalid request body."), 400

        config = current_app.extensions["site_config"]
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="proposal-fee")
        try:
            signed_fee = serializer.loads(str(payload.get("fee_token", "")), max_age=3600)
            signed_amount = int(signed_fee["amount"])
            if signed_amount != int(payload.get("fee_amount", -1)):
                raise BadSignature("Fee amount mismatch")
        except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
            return jsonify(error="The playful fee expired. Refresh the page and try again."), 400

        clean, error = validate_response(payload, config)
        if error:
            return jsonify(error=error), 400

        response_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        currency = config["fee"].get("currency", "USD")

        database = get_database()
        database.execute(
            """
            INSERT INTO responses
                (id, selected_date, selected_time, food, fee_amount, fee_currency, accepted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                response_id,
                clean["selected_date"],
                clean["selected_time"],
                clean["food"],
                clean["fee_amount"],
                currency,
                clean["accepted"],
                created_at,
            ),
        )
        database.commit()
        return jsonify(id=response_id, status="saved"), 201

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Not found."), 404

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Request is too large."), 413


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        nonce = getattr(g, "csp_nonce", "")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        return response


def register_cli(app: Flask) -> None:
    @app.cli.command("responses")
    def show_responses():
        """Print saved proposal responses from newest to oldest."""
        rows = get_database().execute(
            """
            SELECT selected_date, selected_time, food, fee_amount, fee_currency, created_at
            FROM responses
            ORDER BY created_at DESC
            """
        ).fetchall()
        if not rows:
            click.echo("No responses saved yet.")
            return
        for row in rows:
            click.echo(
                f"{row['selected_date']} {row['selected_time']} | "
                f"{row['food']} | {row['fee_currency']} {row['fee_amount']} | {row['created_at']}"
            )


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
