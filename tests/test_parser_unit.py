from app.parser import (
    norm,
    extract_post,
    extract_times,
    extract_assumption_time,
    extract_date,
    parse_message,
    similarity,
)


def test_norm_removes_accents_and_normalizes_case():
    assert norm("  João da Silva  ") == "JOAO DA SILVA"


def test_extract_post_from_message():
    assert extract_post("Assumindo RO-JIP-EJIP às 07h") == "RO-JIP-EJIP"


def test_extract_times_accepts_common_formats():
    text = "Assumi às 07h e encerrei às 19:30"
    times = extract_times(text)
    assert [item["time"] for item in times] == ["07:00", "19:30"]


def test_extract_assumption_time():
    assert extract_assumption_time("Assumindo serviço às 07h00") == "07:00"


def test_extract_date_with_received_at_fallback():
    assert extract_date(
        "Assumindo serviço",
        received_at="2026-10-11T07:00:00",
    ) == "2026-10-11"


def test_parse_message_returns_expected_fields():
    result = parse_message(
        "CONTROLops",
        "Assumindo RO-JIP-EJIP às 07h00",
        received_at="2026-10-11T07:00:00",
    )

    assert result["group"] == "CONTROLops"
    assert result["post_raw"] == "RO-JIP-EJIP"
    assert result["assumption_time"] == "07:00"
    assert result["date"] == "2026-10-11"


def test_similarity_handles_equivalent_names():
    assert similarity("João da Silva", "Joao da Silva") > 90
