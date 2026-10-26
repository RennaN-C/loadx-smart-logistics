import uuid
from io import BytesIO

from sqlalchemy import func, select

from app.modules.deliveries.models import Delivery, Trip
from app.modules.loading.models import LoadingSession
from app.modules.status_history.models import StatusHistory
from tests.integration.oc90_helpers import seed_multi_flow


def test_two_trucks_complete_independent_legs_and_aggregate_order(
    client, session_factory
):
    s = seed_multi_flow(client, session_factory)
    assert len(s.parts) == 2
    assert {p["load_plan"]["status"] for p in s.parts} == {"CALCULATED"}
    s.approve()
    assert s.status() == "PLANNED"
    assert {p["load_plan"]["status"] for p in s.parts} == {"APPROVED"}
    s.prepare_loadings()
    identities = []
    for index, part in enumerate(s.parts):
        plan = part["load_plan"]
        identities.append(
            {(item["order_item_id"], item["volume_index"]) for item in plan["items"]}
        )
        assert {item["load_plan_item_id"] for item in s.loadings[index]["items"]} == {
            item["id"] for item in plan["items"]
        }
        assert s.create_loading(index) == s.loadings[index]
    assert identities[0].isdisjoint(identities[1])
    assert set.union(*identities) == {
        (s.order["items"][0]["id"], 1),
        (s.order["items"][0]["id"], 2),
    }
    assert s.parts[0]["load_plan"]["truck_id"] != s.parts[1]["load_plan"]["truck_id"]

    s.finish_loading(0)
    s.trips = [s.create_trip(i) for i in range(2)]
    for index in range(2):
        conflict = s.request(
            "POST",
            "/trips",
            {
                "load_plan_id": s.parts[index]["load_plan"]["id"],
                "driver_id": s.drivers[index]["id"],
            },
            expected=409,
        )
        assert conflict["code"] == "TRIP_LOAD_PLAN_ALREADY_ASSIGNED"
        assert (
            s.trips[index]["deliveries"][0]["distribution_part_id"]
            == s.parts[index]["id"]
        )

    failed = s.trip_status(1, "IN_ROUTE", expected=409)
    assert failed["code"] == "TRIP_LOADING_NOT_FINISHED"
    assert s.status() == "PLANNED"
    s.trip_status(0, "IN_ROUTE")
    assert s.status() == "IN_TRANSIT"
    receipt_a = s.complete_delivery(0)
    assert s.status() == "IN_TRANSIT"
    finished_a = s.trip_status(0, "FINISHED")
    assert (
        s.trip_status(1, "IN_ROUTE", expected=409)["code"]
        == "TRIP_LOADING_NOT_FINISHED"
    )
    assert s.request("GET", f"/trips/{s.trips[0]['id']}") == finished_a
    assert (
        s.request("POST", f"/deliveries/{receipt_a['delivery_id']}/receipt", {})
        == receipt_a
    )

    s.finish_loading(1)
    s.trip_status(1, "IN_ROUTE")
    assert s.status() == "IN_TRANSIT"
    s.trip_status(1, "IN_ROUTE")
    receipt_b = s.complete_delivery(1)
    assert receipt_a["id"] != receipt_b["id"]
    assert s.status() == "DELIVERED"
    s.trip_status(1, "FINISHED")
    s.trip_status(1, "FINISHED")
    assert (
        s.request("POST", f"/deliveries/{receipt_b['delivery_id']}/receipt", {})
        == receipt_b
    )

    # Extract the actual PDF text, including physical identities, not just MIME/magic.
    from pypdf import PdfReader

    for index, part in enumerate(s.parts):
        truck = s.request("GET", f"/trucks/{part['load_plan']['truck_id']}")
        for resource, identifier in [
            ("load-plans", part["load_plan"]["id"]),
            ("trips", s.trips[index]["id"]),
        ]:
            report = client.get(
                f"/api/v1/reports/{resource}/{identifier}", headers=s.headers
            )
            assert report.status_code == 200
            assert report.headers["content-type"] == "application/pdf"
            text = "\n".join(
                page.extract_text() for page in PdfReader(BytesIO(report.content)).pages
            )
            compact_text = "".join(text.split())
            for required in (
                s.distribution["id"],
                part["id"],
                part["load_plan"]["id"],
                s.order["items"][0]["id"],
            ):
                assert required in compact_text
            assert s.parts[1 - index]["id"] not in compact_text
            assert truck["plate"] in text
            assert "VOLUMESDAPARTE1" in compact_text
            volume = part["load_plan"]["items"][0]
            if resource == "load-plans":
                assert (
                    f"({volume['order_item_id']},{volume['volume_index']})"
                    in compact_text
                )
            else:
                assert (
                    f"{volume['order_item_id']}{volume['volume_index']}{volume['order_id']}"
                    in compact_text
                )

    with session_factory() as db:
        plan_ids = [uuid.UUID(p["load_plan"]["id"]) for p in s.parts]
        assert (
            db.scalar(
                select(func.count())
                .select_from(LoadingSession)
                .where(LoadingSession.load_plan_id.in_(plan_ids))
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Trip)
                .where(Trip.load_plan_id.in_(plan_ids))
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Delivery)
                .where(Delivery.order_id == uuid.UUID(s.order["id"]))
            )
            == 2
        )
        history = db.scalars(
            select(StatusHistory).where(StatusHistory.changed_by == s.manager_id)
        ).all()
        transitions = [
            (h.entity_type, str(h.entity_id), h.old_status, h.new_status)
            for h in history
        ]
        for old, new in [("PLANNED", "IN_TRANSIT"), ("IN_TRANSIT", "DELIVERED")]:
            assert transitions.count(("ORDER", s.order["id"], old, new)) == 1
        for trip in s.trips:
            assert transitions.count(("TRIP", trip["id"], "SCHEDULED", "IN_ROUTE")) == 1
            assert transitions.count(("TRIP", trip["id"], "IN_ROUTE", "FINISHED")) == 1
            assert (
                transitions.count(
                    (
                        "DELIVERY",
                        trip["deliveries"][0]["id"],
                        "IN_DELIVERY",
                        "DELIVERED",
                    )
                )
                == 1
            )
    for entity_type, identifier in [
        ("LOAD_DISTRIBUTION", s.distribution["id"]),
        *[("LOAD_DISTRIBUTION_PART", p["id"]) for p in s.parts],
    ]:
        audit = s.request(
            "GET", f"/audit?entity_type={entity_type}&entity_id={identifier}"
        )
        assert any(entry["new_status"] == "APPROVED" for entry in audit["items"])
