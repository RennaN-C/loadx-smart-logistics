"""UI02: Chromium real, API local e PostgreSQL 16 descartável; sem pentest compartilhada."""
import json
import re
import socket
import threading
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from sqlalchemy import func, select

from app.modules.deliveries.cancellation_service import TripCancellation
from app.modules.deliveries.models import Trip
from app.modules.load_planning.models import LoadPlan
from app.modules.status_history.models import StatusHistory

from app.core.config import settings
from app.database.session import get_db
from app.main import app
from app.modules.access_profiles.models import AccessProfile
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_deliveries_api import (
    create_trip, seed_operational_scenario,
)

pytest_plugins = ("tests.integration.conftest",)

ROOT = Path(__file__).resolve().parents[2]
URL = "http://localhost:5173"
SIZES = (375, 768, 1280, 1920)


def ready(port):
    if port not in (5173, 8000):
        raise ValueError("Apenas serviços locais de QA são permitidos")
    for _ in range(90):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    raise AssertionError("Servidor local de QA não iniciou")


def browser_context(browser, headers, width=1280, theme="light"):
    ctx = browser.new_context(
        viewport={"width": width, "height": 800}, color_scheme=theme,
    )
    ctx.add_cookies([{
        "name": settings.session_cookie_name,
        "value": headers["Cookie"].split("=", 1)[1],
        "url": URL, "httpOnly": True, "sameSite": "Lax",
    }])
    return ctx


def test_ui02_browser_five_profiles_and_operations(committed_session_factory):
    """Sessões sintéticas são fixtures; não representam teste de MFA ou login."""
    session_factory = committed_session_factory
    def db_for_local_server():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = db_for_local_server
    server = None
    screenshots = ROOT / "ui02-evidence"
    screenshots.mkdir(parents=True, exist_ok=True)
    failures = []
    try:
        with TestClient(app, raise_server_exceptions=False, headers={"Origin": URL}) as api:
            scenario = seed_operational_scenario(session_factory)
            with session_factory() as db:
                profile = AccessProfile(
                    name="Custom sem acesso", name_key="custom sem acesso",
                    description="Fixture local", active=True,
                )
                db.add(profile)
                db.flush()
                user = User(
                    name="Perfil Custom", email=f"custom-{uuid.uuid4().hex}@example.test",
                    password_hash=uuid.uuid4().hex, role="CUSTOM",
                    custom_profile_id=profile.id, active=True,
                )
                db.add(user)
                db.commit()
                custom_id = user.id
            users = {
                "ADMIN": scenario.admin_headers,
                "LOGISTICS_MANAGER": scenario.manager_headers,
                "CHECKER": scenario.checker_headers,
                "DRIVER": scenario.driver_headers,
                "CUSTOM": issue_session_headers(session_factory, custom_id),
            }
            expected = {
                "ADMIN": (200, 200), "LOGISTICS_MANAGER": (200, 200),
                "CHECKER": (200, 403), "DRIVER": (403, 200),
                "CUSTOM": (403, 403),
            }
            loading_resp = api.post(
                "/api/v1/loading-sessions",
                json={"load_plan_id": str(scenario.load_plan_id)},
                headers=scenario.manager_headers,
            )
            assert loading_resp.status_code == 201
            loading = loading_resp.json()
            trip = create_trip(api, scenario)
            # A separate fleet reservation is necessary for an eligible
            # cancellation: the first trip has a loading session already.
            cancel_scenario = seed_operational_scenario(session_factory)
            cancel_trip = create_trip(api, cancel_scenario)
            eligibility = api.get(
                f"/api/v1/trips/{cancel_trip['id']}/cancellation-preflight",
                headers=cancel_scenario.manager_headers,
            )
            assert eligibility.status_code == 200
            assert eligibility.json()["safe_for_cancellation_workflow"] is True
            for role, headers in users.items():
                assert api.get("/api/v1/auth/me", headers=headers).status_code == 200
                assert tuple(
                    api.get(path, headers=headers).status_code
                    for path in ("/api/v1/loading-sessions", "/api/v1/deliveries")
                ) == expected[role], role

            import uvicorn
            server = uvicorn.Server(uvicorn.Config(
                app, host="127.0.0.1", port=8000, log_level="warning", lifespan="off",
            ))
            threading.Thread(target=server.run, daemon=True).start()
            ready(8000)
            ready(5173)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    for role, headers in users.items():
                        with browser_context(browser, headers) as ctx:
                            page = ctx.new_page()
                            page.on("pageerror", lambda error: failures.append(str(error)))
                            page.goto(URL + "/")
                            page.locator("main").first.wait_for(timeout=30000)
                    for width in SIZES:
                        for theme in ("light", "dark"):
                            for name, headers, url, heading in (
                                ("loading", scenario.checker_headers, "/loading-sessions", "Carregamentos"),
                                ("deliveries", scenario.manager_headers, "/deliveries", "Entregas"),
                            ):
                                with browser_context(browser, headers, width, theme) as ctx:
                                    page = ctx.new_page()
                                    page.on("pageerror", lambda error: failures.append(str(error)))
                                    page.goto(URL + url)
                                    page.get_by_role("heading", name=heading).wait_for()
                                    assert page.evaluate(
                                        "document.documentElement.scrollWidth <= innerWidth + 2"
                                    ), (name, width, theme)
                                    page.screenshot(path=str(screenshots / f"{name}-{width}-{theme}.png"))

                    with browser_context(browser, scenario.checker_headers) as ctx:
                        page = ctx.new_page()
                        page.goto(URL + f"/loading/{loading['id']}")
                        page.get_by_role("heading", name="Conferência do carregamento").wait_for()
                        page.get_by_role("link", name="Voltar aos carregamentos").wait_for()
                        page.get_by_role("button", name="Iniciar conferência").click()
                        field = page.get_by_role("textbox", name="LER CÓDIGO DO VOLUME")
                        field.wait_for(state="visible")
                        field.fill(loading["items"][0]["code"])
                        field.press("Enter")
                        page.locator(".scan-result").get_by_text(re.compile("Conferido")).wait_for()
                        assert field.evaluate("(el) => document.activeElement === el")
                        page.reload()
                        page.get_by_role("heading", name="Conferência do carregamento").wait_for()

                    with browser_context(browser, scenario.manager_headers) as ctx:
                        page = ctx.new_page()
                        page.goto(URL + f"/trips/{trip['id']}")
                        page.get_by_role("heading", name="Acompanhamento da viagem").wait_for()
                        page.get_by_role("button", name="Verificar bloqueios").click()
                        page.get_by_text(re.compile("Cancelamento bloqueado|Pré-validação aprovada")).wait_for()
                        page.screenshot(path=str(screenshots / "oc94-preflight.png"))

                        # Finalizar a conferência com o backend real e iniciar a viagem.
                        current = api.get(
                            f"/api/v1/loading-sessions/{loading['id']}",
                            headers=scenario.checker_headers,
                        )
                        assert current.status_code == 200
                        for item in current.json()["items"]:
                            if item["status"] != "PENDING":
                                continue
                            checked = api.patch(
                                f"/api/v1/loading-sessions/{loading['id']}/items/{item['id']}",
                                json={"status": "CHECKED"},
                                headers=scenario.checker_headers,
                            )
                            assert checked.status_code == 200
                        finished = api.patch(
                            f"/api/v1/loading-sessions/{loading['id']}/status",
                            json={"status": "FINISHED"},
                            headers=scenario.checker_headers,
                        )
                        assert finished.status_code == 200
                        page.get_by_role("button", name="Iniciar viagem").click()
                        page.get_by_role(
                            "button", name="Consultar ou registrar ocorrência",
                        ).wait_for(timeout=20000)
                        page.get_by_role(
                            "button", name="Consultar ou registrar ocorrência",
                        ).click()
                        page.get_by_label(
                            "Motivo (mínimo de 10 caracteres)",
                        ).fill("Cliente não localizado no endereço de entrega")
                        page.get_by_role(
                            "button", name="Registrar no histórico",
                        ).click()
                        page.get_by_text(
                            "Ocorrência registrada no histórico da entrega.",
                        ).wait_for(timeout=20000)
                        page.screenshot(path=str(screenshots / "oc94-ocorrencia.png"))

                        # Interrupção e retomada devem continuar transações distintas.
                        panel = page.get_by_role(
                            "region", name="Interrupção e retomada da viagem",
                        )
                        panel.get_by_role("button", name="Interromper viagem").click()
                        panel.get_by_role(
                            "textbox", name=re.compile("Motivo obrigatório"),
                        ).fill("Falha mecânica simulada na rota")
                        panel.get_by_role(
                            "button", name="Confirmar interrupção",
                        ).click()
                        panel.get_by_role(
                            "button", name="Retomar viagem",
                        ).wait_for(timeout=20000)
                        panel.get_by_role("button", name="Retomar viagem").click()
                        panel.get_by_role(
                            "textbox", name=re.compile("Motivo obrigatório"),
                        ).fill("Reparo concluído em ambiente isolado")
                        panel.get_by_role("button", name="Confirmar retomada").click()
                        page.get_by_role(
                            "button", name="Consultar ou registrar ocorrência",
                        ).wait_for(timeout=20000)
                        page.screenshot(path=str(screenshots / "oc94-retomada.png"))

                    # A second journey exercises the actual UI cancellation,
                    # separate from the loaded/started trip.
                    with browser_context(browser, cancel_scenario.manager_headers) as ctx:
                        page = ctx.new_page()
                        page.goto(URL + f"/trips/{cancel_trip['id']}")
                        page.get_by_role(
                            "heading", name="Acompanhamento da viagem",
                        ).wait_for()
                        page.get_by_role("button", name="Verificar bloqueios").click()
                        page.get_by_text("Pré-validação aprovada.", exact=False).wait_for()
                        page.get_by_role("button", name="Solicitar cancelamento").click()
                        reason = "Reprogramação operacional testada no Chromium"
                        page.get_by_role(
                            "textbox", name="Motivo do cancelamento",
                        ).fill(reason)
                        page.get_by_role("button", name="Confirmar cancelamento").click()
                        page.get_by_text("Cancelada", exact=True).first.wait_for()
                        page.screenshot(path=str(screenshots / "oc94-cancelamento.png"))

                    persisted = api.get(
                        f"/api/v1/trips/{cancel_trip['id']}",
                        headers=cancel_scenario.manager_headers,
                    )
                    assert persisted.status_code == 200
                    assert persisted.json()["status"] == "CANCELED"
                    assert all(
                        delivery["status"] == "CANCELED"
                        for delivery in persisted.json()["deliveries"]
                    )
                    with session_factory() as db:
                        canceled_id = uuid.UUID(cancel_trip["id"])
                        ledger = db.scalar(
                            select(TripCancellation).where(
                                TripCancellation.trip_id == canceled_id
                            )
                        )
                        assert ledger is not None and ledger.reason == reason
                        assert db.scalar(
                            select(func.count()).select_from(TripCancellation).where(
                                TripCancellation.trip_id == canceled_id
                            )
                        ) == 1
                        assert db.scalar(
                            select(func.count()).select_from(StatusHistory).where(
                                StatusHistory.entity_type == "TRIP",
                                StatusHistory.entity_id == canceled_id,
                                StatusHistory.new_status == "CANCELED",
                            )
                        ) == 1
                        assert db.get(Trip, canceled_id).status == "CANCELED"
                        assert db.get(LoadPlan, cancel_scenario.load_plan_id).status == "APPROVED"
                        key = str(ledger.idempotency_key)
                        cancellation_event_id = str(ledger.id)
                    path = f"/api/v1/trips/{cancel_trip['id']}/cancellation"
                    payload = {"reason": reason, "idempotency_key": key}
                    replay = api.post(
                        path, json=payload, headers=cancel_scenario.manager_headers,
                    )
                    assert replay.status_code == 200
                    assert replay.json()["id"] == cancellation_event_id
                    assert api.post(
                        path, json=payload, headers=cancel_scenario.checker_headers,
                    ).status_code == 403
                    assert api.post(
                        path, json={
                            **payload,
                            "reason": "Motivo divergente para a mesma solicitação",
                        }, headers=cancel_scenario.manager_headers,
                    ).status_code == 409

                    # UI04-sized viewport matrix for the OC94 trip details.
                    # The tests keep the same authenticated manager and live API.
                    for width in SIZES:
                        for theme in ("light", "dark"):
                            with browser_context(
                                browser, scenario.manager_headers, width, theme,
                            ) as ctx:
                                page = ctx.new_page()
                                page.goto(URL + f"/trips/{trip['id']}")
                                page.get_by_role(
                                    "heading", name="Acompanhamento da viagem",
                                ).wait_for()
                                page.get_by_role(
                                    "region", name="Interrupção e retomada da viagem",
                                ).wait_for()
                                assert page.evaluate(
                                    "document.documentElement.scrollWidth <= innerWidth + 2"
                                ), ("oc94", width, theme)
                                page.screenshot(path=str(
                                    screenshots / f"oc94-detalhes-{width}-{theme}.png"
                                ))

                    # The assigned driver may read the trip but must never see
                    # the manager-only cancellation/interruption controls.
                    with browser_context(browser, scenario.driver_headers) as ctx:
                        page = ctx.new_page()
                        page.goto(URL + f"/trips/{trip['id']}")
                        page.get_by_role(
                            "heading", name="Acompanhamento da viagem",
                        ).wait_for()
                        assert page.get_by_role(
                            "button", name="Verificar bloqueios",
                        ).count() == 0
                        assert page.get_by_role(
                            "region", name="Interrupção e retomada da viagem",
                        ).count() == 0
                finally:
                    browser.close()
        assert failures == [], failures[:3]
        (screenshots / "resultado.json").write_text(json.dumps({
            "result": "passed", "roles": list(users),
            "viewports": list(SIZES), "themes": ["light", "dark"],
            "real_api": True, "postgresql_isolated": True,
            "limits": ["MFA login not tested", "physical scanner not tested", "cancellation validated with real browser and PostgreSQL"],
        }, indent=2), encoding="utf-8")
    finally:
        if server is not None:
            server.should_exit = True
        app.dependency_overrides.clear()
