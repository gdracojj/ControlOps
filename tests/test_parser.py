
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.parser import parse_message


BASE_DIR = Path(__file__).resolve().parent.parent

FILE = BASE_DIR / "data" / "test_messages_1000.json"
FAILURES_FILE = BASE_DIR / "data" / "parser_failures.json"


with open(FILE, "r", encoding="utf-8") as f:
    messages = json.load(f)


total = len(messages)
ok = 0
falhas = 0
failure_list = []

for item in messages:
    resultado = parse_message(
        item.get("group", "CONTROLops"),
        item["message"],
    )

    status_esperado = item.get("status_teste")

    post_extraido = bool(resultado.get("post_raw"))
    horario_extraido = bool(resultado.get("assumption_time"))

    # Mensagens incompletas devem ter posto, mas não horário.
    if status_esperado == "incompleta":
        passou = post_extraido and not horario_extraido

    # Para os demais cenários, preservamos o critério original.
    else:
        passou = post_extraido and horario_extraido

    if passou:
        ok += 1
    else:
        falhas += 1
        failure_list.append({
            "id": item.get("id"),
            "status_teste": status_esperado,
            "message": item["message"],
            "parser_result": resultado,
        })


with open(FAILURES_FILE, "w", encoding="utf-8") as f:
    json.dump(
        failure_list,
        f,
        ensure_ascii=False,
        indent=2,
    )


print("=" * 50)
print("       TESTE DO PARSER - CONTROLops")
print("=" * 50)
print(f"Total:       {total}")
print(f"Parser OK:   {ok}")
print(f"Falhas:      {falhas}")

if total > 0:
    print(f"Taxa OK:     {(ok / total) * 100:.2f}%")

print("-" * 50)
print("Falhas salvas em:")
print(FAILURES_FILE)
print("=" * 50)
