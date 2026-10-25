import pytest

from scripts.seed_demo import demo_customers, demo_drivers, validate_target


@pytest.mark.parametrize(
    "environment,host,database",
    [
        ("production", "db", "loadx"),
        ("local", "external.invalid", "loadx"),
        ("local", "127.0.0.1", "loadx_test"),
        ("local", None, "loadx"),
    ],
)
def test_seed_rejects_non_local_application_targets(environment, host, database):
    with pytest.raises(ValueError, match="somente no banco loadx local"):
        validate_target(environment, host, database)


def test_demo_registrations_are_deterministic_unique_and_pass_domain_schemas():
    customers = demo_customers()
    drivers = demo_drivers()
    assert customers == demo_customers()
    assert drivers == demo_drivers()
    assert len({item.document for item in [*customers, *drivers]}) == 14
    assert len({item.license_number for item in drivers}) == 6
    assert all(item.name.startswith("DEMO ") for item in [*customers, *drivers])
    validate_target("local", "db", "loadx")
