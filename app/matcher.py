
import json
import re
from datetime import date, datetime
from pathlib import Path

from .parser import similarity


BASE = Path(__file__).resolve().parent.parent
SCALE_PATH = BASE / "data" / "escala.json"
ALIASES_PATH = BASE / "data" / "aliases.json"

VALID_PLANTOES = {
    "diurno_a",
    "noturno_a",
    "diurno_b",
    "noturno_b",
}

TIME_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})$")


def load_json(path: Path):
    """Carrega um arquivo JSON de configuração."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


SCALE = load_json(SCALE_PATH)
ALIASES = load_json(ALIASES_PATH)


def canonical_post(post):
    """Normaliza o código do posto e aplica aliases conhecidos."""
    if post is None:
        return None

    value = str(post).strip().upper()
    if not value:
        return None

    value = value.replace("P0STO-", "POSTO-")
    value = re.sub(r"^POSTO[-\s]+", "", value)

    return ALIASES.get(value, value)


def parse_date(value):
    """Converte datas ISO ou brasileiras para datetime.date."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()
    if not value:
        return None

    # ISO: 2026-10-10 ou 2026-10-10T06:30:00
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except ValueError:
        pass

    # BR: 10/10/2026, com ou sem horário
    for fmt in (
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def day_parity(value):
    """Retorna 'pares' ou 'impares' conforme o dia do mês."""
    parsed = parse_date(value)

    if parsed is None:
        return None

    return "pares" if parsed.day % 2 == 0 else "impares"


def get_expected(plantao, message_date=None):
    """
    Retorna os colaboradores ativos do plantão selecionado.

    Quando há data, também exige compatibilidade com a paridade.
    Sem data válida, utiliza o plantão informado sem inferir paridade.
    """
    if plantao not in VALID_PLANTOES:
        return []

    parity = day_parity(message_date)

    return [
        item
        for item in SCALE
        if item.get("plantao") == plantao
        and item.get("active", True)
        and (
            parity is None
            or item.get("dias") == parity
        )
    ]


def best_employee(name, expected):
    """Escolhe o colaborador esperado mais parecido com o nome recebido."""
    if not expected:
        return None, 0

    # Sem nome, preserva a identificação pelo posto e horário.
    # A ausência do nome não deve transformar o posto em desconhecido.
    if not name:
        return expected[0], 0

    best = max(
        expected,
        key=lambda item: similarity(
            name,
            item.get("employee", ""),
        ),
    )

    score = similarity(name, best.get("employee", ""))

    return best, score


def parse_time_minutes(value):
    """Converte HH:MM em minutos desde meia-noite; inválido retorna None."""
    if not value:
        return None

    match = TIME_PATTERN.fullmatch(str(value).strip())
    if not match:
        return None

    hour, minute = map(int, match.groups())

    if hour > 23 or minute > 59:
        return None

    return hour * 60 + minute


def time_delta(actual, expected):
    """Calcula a diferença em minutos entre o horário real e o esperado."""
    actual_minutes = parse_time_minutes(actual)
    expected_minutes = parse_time_minutes(expected)

    if actual_minutes is None or expected_minutes is None:
        return None

    return actual_minutes - expected_minutes


def _base_result(parsed, status, post=None):
    """Mantém uma estrutura uniforme para os resultados do matcher."""
    return {
        "status": status,
        "post": post,
        "incoming": parsed.get("incoming"),
        "assumption_time": parsed.get("assumption_time"),
        "expected_employee": None,
        "expected_time": None,
        "time_status": None,
        "delta_minutes": None,
        "employee_divergence": False,
        "possible_wrong_group": False,
        "employee_similarity": 0,
        "confidence": 0,
        "date": parsed.get("date"),
        "dias": None,
    }


def classify(parsed, expected):
    """Classifica uma mensagem contra a escala compatível com o relatório."""
    post = canonical_post(parsed.get("post_raw"))
    incoming = parsed.get("incoming")

    if not post:
        return _base_result(
            parsed,
            "POSTO_NAO_LOCALIZADO",
        )

    same_post = [
        item
        for item in expected
        if canonical_post(
            item.get("posto") or item.get("post")
        ) == post
    ]

    if not same_post:
        return _base_result(
            parsed,
            "POSTO_NAO_LOCALIZADO",
            post=post,
        )

    expected_item, score = best_employee(incoming, same_post)

    if expected_item is None:
        return _base_result(
            parsed,
            "POSTO_NAO_LOCALIZADO",
            post=post,
        )

    expected_time = expected_item.get("expected_time")
    actual_time = parsed.get("assumption_time")
    delta = time_delta(actual_time, expected_time)

    if delta is None:
        time_status = "HORÁRIO NÃO IDENTIFICADO"
    elif delta == 0:
        time_status = "REGULAR"
    elif delta < 0:
        time_status = f"ADIANTADO {abs(delta)} min"
    else:
        time_status = f"ATRASADO {delta} min"

    employee_match = score >= 70

    result = {
        "status": "ASSUNÇÃO_IDENTIFICADA",
        "post": expected_item.get("posto") or expected_item.get("post"),
        "incoming": incoming,
        "assumption_time": actual_time,
        "expected_employee": expected_item.get("employee"),
        "expected_time": expected_time,
        "time_status": time_status,
        "delta_minutes": delta,
        "employee_divergence": bool(incoming) and not employee_match,
        "employee_similarity": round(score, 1),
        # O ID do grupo não é necessariamente o código do posto.
        # Só habilitar esta alerta quando existir mapeamento explícito.
        "possible_wrong_group": False,
        "confidence": round(score, 1),
        "date": parsed.get("date"),
        "dias": expected_item.get("dias"),
    }

    return result


def build_report(messages, plantao):
    """
    Monta um relatório diário para o plantão selecionado.

    Usa a data válida mais recente do histórico como referência.
    Só inclui mensagens dessa data, evitando misturar ocorrências de
    dias diferentes com uma única lista de postos esperados.
    """
    if plantao not in VALID_PLANTOES:
        plantao = "diurno_a"

    parsed_messages = list(messages)

    dates = [
        parsed_date
        for parsed_date in (
            parse_date(message.get("date"))
            for message in parsed_messages
        )
        if parsed_date is not None
    ]

    reference_date = max(dates) if dates else None
    expected = get_expected(plantao, reference_date)

    if reference_date is None:
        # Sem datas válidas, não é possível separar o histórico por dia.
        report_messages = parsed_messages
    elif not expected:
        # O ciclo selecionado não corresponde à paridade da data.
        # Não classificar mensagens contra uma escala incompatível.
        report_messages = []
    else:
        report_messages = [
            message
            for message in parsed_messages
            if parse_date(message.get("date")) == reference_date
        ]

    expected_posts = {
        canonical_post(item.get("posto") or item.get("post"))
        for item in expected
    }
    expected_posts.discard(None)

    results = []
    seen_posts = set()

    for parsed in report_messages:
        result = classify(parsed, expected)
        result["raw"] = parsed.get("raw", "")
        result["group"] = parsed.get("group")
        result["plantao"] = plantao

        results.append(result)

        if result.get("status") == "ASSUNÇÃO_IDENTIFICADA":
            post = canonical_post(result.get("post"))
            if post in expected_posts:
                seen_posts.add(post)

    missing = []
    seen_missing_posts = set()

    for item in expected:
        post = canonical_post(item.get("posto") or item.get("post"))

        if not post or post in seen_posts or post in seen_missing_posts:
            continue

        missing.append(item)
        seen_missing_posts.add(post)

    return {
        "plantao": plantao,
        "expected_total": len(expected_posts),
        "identified_total": len(seen_posts),
        "missing": missing,
        "results": results,
        "reference_date": (
            reference_date.isoformat()
            if reference_date
            else None
        ),
    }
