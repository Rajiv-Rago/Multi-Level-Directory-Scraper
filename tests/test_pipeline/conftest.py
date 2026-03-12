"""Shared fixtures for pipeline tests."""

from datetime import datetime, timezone

import pytest

from models.record import DirectoryRecord
from validation.collector import ValidationCollector


@pytest.fixture()
def sample_records():
    now = datetime.now(timezone.utc)
    return [
        DirectoryRecord(
            region="Northeast",
            category="Restaurants",
            name="Complete Cafe",
            address="123 Main St",
            phone="+14155551234",
            website="https://completecafe.com",
            description="A complete record",
            source_url="https://example.com/listings/1",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="Northeast",
            category="Restaurants",
            name="No Address Place",
            address=None,
            phone="(415) 555-1234",
            website="https://noaddress.com",
            description="Missing address",
            source_url="https://example.com/listings/2",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="Southwest",
            category="Hotels",
            name="  Raw Phone Hotel  ",
            address="456 Oak Ave",
            phone="(415) 555-9876",
            website="/about",
            description="Has a raw phone number",
            source_url="https://example.com/listings/3",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="Southwest",
            category="Hotels",
            name="Caf\u00e9 &amp; Bar",
            address="789 Elm St",
            phone="+44 20 8366 1177",
            website="../other",
            description="Has HTML   entities\n\tand whitespace",
            source_url="https://example.com/dir/page",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="Northeast",
            category="Restaurants",
            name="Complete Cafe",
            address="123 Main St",
            phone=None,
            website=None,
            description=None,
            source_url="https://example.com/listings/5",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="West",
            category="Shops",
            name="Invalid Phone Shop",
            address="999 Pine St",
            phone="not-a-phone",
            website="not-a-url",
            description="Has invalid data",
            source_url="https://example.com/listings/6",
            scraped_at=now,
        ),
    ]


@pytest.fixture()
def sample_config():
    return {
        "default_country_code": "US",
        "base_url": "https://example.com",
        "output_dir": "./output",
    }


@pytest.fixture()
def collector():
    return ValidationCollector()
