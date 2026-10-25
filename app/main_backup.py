from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path

from .parser import parse_message
from .matcher import build_report
from .storage import load_messages, add_message, clear_messages


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE = Path(__file__).resolve().parent.parent

SCALE = json.loads(
    (BASE / "data" / "escala.json").read_text(
        encoding="utf-8"
    )
)

app = FastAPI(
    title="VTAL CCOR V2"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory=str(BASE / "app" / "templates")
)


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=Path(__file__).resolve().parent / "static"
    ),
    name="static"
)


# ============================================================
# MODELOS
# ============================================================

class MessageIn(BaseModel):
    group: str = ""
    message: str
    received_at: str | None = None


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_context(
    request: Request,
    plantao: str
):

    msgs = load_messages()

    plantao_validos = (
        "diurno_a",
        "noturno_a",
        "diurno_b",
        "noturno_b",
    )

    if plantao not in plantao_validos:
        plantao = "diurno_a"

    # --------------------------------------------------------
    # GERA RELATÓRIO
    # --------------------------------------------------------

    report = build_report(
        msgs,
        plantao
    )

    # --------------------------------------------------------
    # CONTADORES
    # --------------------------------------------------------

    counts = {
        "REGULAR": 0,
        "ADIANTADO": 0,
        "ATRASADO": 0,
        "SEM ASSUNÇÃO": len(report["missing"]),
        "DIVERGÊNCIA": 0,
        "IDENTIFICADA": 0,
    }

    results = []

    # --------------------------------------------------------
    # PROCESSA ASSUNÇÕES IDENTIFICADAS
    # --------------------------------------------------------

    for r in report["results"]:

        if r.get("status") != "ASSUNÇÃO_IDENTIFICADA":
            continue

        timing = (
            r.get("time_status")
            or "HORÁRIO NÃO IDENTIFICADO"
        )

        # ----------------------------------------------------
        # STATUS PRINCIPAL
        # ----------------------------------------------------

        if timing == "REGULAR":

            counts["REGULAR"] += 1
            status = "REGULAR"

        elif timing.startswith("ADIANTADO"):

            counts["ADIANTADO"] += 1
            status = "ADIANTADO"

        elif timing.startswith("ATRASADO"):

            counts["ATRASADO"] += 1
            status = "ATRASADO"

        else:

            counts["IDENTIFICADA"] += 1
            status = "IDENTIFICADA"

        # ----------------------------------------------------
        # MOTIVOS / ALERTAS
        # ----------------------------------------------------

        reason_parts = []

        if r.get("employee_divergence"):

            counts["DIVERGÊNCIA"] += 1

            reason_parts.append(
                "Colaborador informado diferente da escala (informativo)."
            )

        if r.get("possible_wrong_group"):

            reason_parts.append(
                "Possível grupo/posto incorreto."
            )

        if not reason_parts:

            reason_parts.append(
                "Assunção identificada."
            )

        # ----------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------

        results.append({
            "status": status,

            "post": r.get(
                "post"
            ),

            "expected_name": r.get(
                "expected_employee"
            ),

            "incoming": r.get(
                "incoming"
            ),

            "actual_time": (
                r.get("actual_time")
                or r.get("assumption_time")
            ),

            "expected_time": r.get(
                "expected_time"
            ),

            "reason": " ".join(
                reason_parts
            ),

            # ALERTA DE DIVERGÊNCIA
            "employee_divergence": r.get(
                "employee_divergence",
                False
            ),

            # PERCENTUAL DE SIMILARIDADE
            "employee_similarity": r.get(
                "employee_similarity"
            ),

            # ALERTA DE GRUPO/POSTO
            "possible_wrong_group": r.get(
                "possible_wrong_group",
                False
            ),
        })

    # --------------------------------------------------------
    # POSTOS SEM ASSUNÇÃO
    # --------------------------------------------------------

    for item in report["missing"]:

        results.append({
            "status": "SEM ASSUNÇÃO",

            "post": item.get(
                "post"
            ),

            "expected_name": item.get(
                "employee"
            ),

            "incoming": None,

            "actual_time": None,

            "expected_time": item.get(
                "expected_time"
            ),

            "reason": (
                "Nenhuma assunção válida "
                "identificada para o posto."
            ),

            "employee_divergence": False,

            "employee_similarity": None,

            "possible_wrong_group": False,
        })

    # --------------------------------------------------------
    # CONTEXTO DO DASHBOARD
    # --------------------------------------------------------

    return {
        "request": request,

        "counts": counts,

        "total_roster": report[
            "expected_total"
        ],

        "results": results,

        "plantao": plantao,
    }


# ============================================================
# ROTA PRINCIPAL
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def dashboard(
    request: Request,
    plantao: str = "diurno_a"
):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=dashboard_context(
            request,
            plantao
        )
    )


# ============================================================
# API - RELATÓRIO
# ============================================================

@app.get("/api/report")
def api_report(
    plantao: str = "diurno_a"
):

    plantao_validos = (
        "diurno_a",
        "noturno_a",
        "diurno_b",
        "noturno_b",
    )

    if plantao not in plantao_validos:
        plantao = "diurno_a"

    return build_report(
        load_messages(),
        plantao
    )


# ============================================================
# API - RECEBER MENSAGEM
# ============================================================

@app.post("/api/messages")
def receive_message(
    payload: MessageIn
):

    received_at = (
        payload.received_at
        or datetime.now().isoformat(
            timespec="seconds"
        )
    )

    parsed = parse_message(
        payload.group,
        payload.message,
        received_at
    )

    add_message(
        parsed
    )

    return parsed


# ============================================================
# API - LIMPAR MENSAGENS
# ============================================================

@app.post("/api/clear")
def api_clear():

    clear_messages()

    return {
        "ok": True
    }


# ============================================================
# API - CARREGAR EXEMPLOS
# ============================================================

@app.post("/api/load-samples")
def load_samples():

    samples = [

        (
            "BA-FSA-GOVS",
            """DATA: 25/09/26
TURNO: 07:00 as 19:00
Assunção de serviço.
Vigia: Gilvan Cerqueira dos Santos
Assumido o plantão sem alteração."""
        ),

        (
            "AC-RBO-RBCE",
            """Assunção de Serviço
Estação AC-RBO-RBCE
Data: 25/09/2026
Vigia: Vaucelio Leve assumo o plantão do vigia (Luiz Lima) às (06h) até às (18h)"""
        ),

        (
            "RO-PVO-EDPO",
            """RO-PVO-EDPO
Data:25/09/2026
Assunção de plantão às 06:54
Silmara
Recebi o posto de Antônio"""
        ),

        (
            "AL-MCO-JT",
            """AL-MCO-JT
Assunção de Serviço
Vigia Anderson Silva estou recebendo o plantão do vigia noturno José Costa da Silva, com turno das 07:00 as 19:00"""
        ),

        (
            "RN-NTL-CTO",
            """POSTO-RN-NTL-CTO
25/09/2026
ASSUNÇÃO DE SERVIÇO
Vigia Jefferson de Oliveira Pinheiro, assumindo o serviço das 07:00hs as 19:00hs
Recebi o serviço do Vigia: Nazareno Barbosa Trajano as 07:00hs."""
        ),

        (
            "PE-RCE-EBVT",
            """PE-RCE-EBVT
25/09/2026
VIGIA: Lucas guedea
HORÁRIO: 07:00 às 19:00h
Assumindo o serviço do vigia Adeilson santos com tudo em ordem sem alteração."""
        ),

        (
            "SE-AJU-AJU",
            """Assunção de serviço
Vigia: João evangelista assumindo o posto de serviço das 07h as 19h do Vigia: Márcio José
Posto V-tal SE AJU
data: 25/09/2026"""
        ),

        (
            "AM-MNS-PA",
            """data: 25/09/2026
AM MNS PA
ASSUNCAO DE SERVIÇOS
SIRLANDO SILVA
SAINDO
ARALDO BITENCOURT"""
        ),
    ]

    clear_messages()

    for group, text in samples:

        received_at = (
            "2026-09-25T07:00:00"
        )

        parsed = parse_message(
            group,
            text,
            received_at
        )

        add_message(
            parsed
        )

    return {
        "loaded": len(samples)
    }


# ============================================================
# PÁGINA DE TESTES
# ============================================================

@app.get(
    "/teste",
    response_class=HTMLResponse
)
def test_page(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="test.html",
        context={
            "request": request
        }
    )
