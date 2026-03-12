"""Phone normalization pipeline stage."""

import phonenumbers

from models.record import DirectoryRecord
from validation.collector import ValidationCollector


def _normalize_phone(number_str: str, default_country_code: str) -> tuple[str, bool]:
    if not number_str or not number_str.strip():
        return number_str, False
    try:
        parsed = phonenumbers.parse(number_str.strip(), default_country_code)
        if phonenumbers.is_valid_number(parsed):
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            return formatted, True
        return number_str, False
    except phonenumbers.NumberParseException:
        return number_str, False


def normalize_phones(
    records: list[DirectoryRecord],
    collector: ValidationCollector,
    default_country_code: str,
) -> list[DirectoryRecord]:
    normalized_count = 0
    failed_count = 0
    result = []

    for record in records:
        if record.phone is None or record.phone == "":
            result.append(record)
            continue

        formatted, was_normalized = _normalize_phone(record.phone, default_country_code)

        if was_normalized:
            normalized_count += 1
        else:
            failed_count += 1
            collector.add_warning(
                "phone",
                record.phone,
                f"Could not parse or invalid phone number: {record.phone}",
                record.source_url,
            )

        result.append(record.model_copy(update={"phone": formatted}))

    collector.add_stat("phones_normalized", normalized_count)
    collector.add_stat("phones_failed", failed_count)
    return result
