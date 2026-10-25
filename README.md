# ControlOps

Aplicação Python com API FastAPI para interpretar mensagens de assunção de serviço e compará-las com uma escala operacional.

## Problema e funcionalidades

Mensagens operacionais podem chegar em texto livre, com horários, postos e nomes em formatos diferentes. O ControlOps extrai os campos reconhecidos, compara-os com a escala configurada e apresenta resultados em uma API e em um dashboard.

O repositório implementa:

- extração de posto, colaborador, horário e data pelo parser;
- normalização e comparação textual de nomes e postos;
- correspondência com escala por plantão e paridade do dia;
- classificação de horários e identificação de postos sem assunção;
- API FastAPI, dashboard HTML e armazenamento local em JSON;
- cliente opcional Node.js para encaminhar mensagens de grupos do WhatsApp;
- gerador de mensagens e testes do parser.

A integração com WhatsApp requer configuração própria. No cliente, a lista de grupos monitorados está vazia por padrão; nesse estado, todas as mensagens de grupos são encaminhadas. Configure a lista antes de iniciar o cliente e use apenas grupos autorizados.

## Requisitos

- Python 3.10 ou superior;
- Node.js e npm apenas para usar o cliente opcional do WhatsApp;
- dependências Python listadas em `requirements.txt`.

## Stack

- Python, FastAPI, Pydantic, Jinja2 e RapidFuzz;
- HTML, CSS e JavaScript no dashboard;
- JSON para escala, aliases e armazenamento local;
- Node.js, `whatsapp-web.js` e `qrcode-terminal` para a integração opcional.

## Instalação e execução

Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

No Windows PowerShell, ative o ambiente com `.venv\Scripts\Activate.ps1` no lugar do comando `source`. A aplicação fica disponível em <http://127.0.0.1:8000>.

O cliente opcional do WhatsApp é iniciado separadamente, depois da API e da configuração de grupos:

```bash
npm ci
node whatsapp/client.js
```

O cliente solicita autenticação pelo QR Code e encaminha mensagens para `http://127.0.0.1:8000/api/messages`.

## Testes

Gere o conjunto local de mensagens e execute o teste de parser que o consome:

```bash
python tests/generate_messages.py
python tests/test_parser.py
```

Os testes unitários em `tests/test_parser_unit.py` usam pytest. Para executá-los, instale pytest no ambiente e rode:

```bash
python -m pip install pytest
python -m pytest -q
```

O gerador cria `data/test_messages_1000.json` e o teste grava `data/parser_failures.json`; ambos são artefatos locais ignorados pelo Git.

## API e formato de entrada

- `GET /` — dashboard;
- `GET /api/report?plantao=diurno_a` — relatório do plantão (`diurno_a`, `noturno_a`, `diurno_b` ou `noturno_b`);
- `POST /api/messages` — recebe e processa uma mensagem;
- `POST /api/refresh` — substitui o conjunto de mensagens pelo lote enviado;
- `POST /api/clear` — limpa o armazenamento local;
- `GET /teste` — página de testes da interface.

O corpo esperado por `POST /api/messages` é:

```json
{
  "group": "ID_DO_GRUPO",
  "message": "texto da mensagem operacional",
  "received_at": "2026-10-25T06:00:00"
}
```

`group` e `received_at` são opcionais; `message` é obrigatório. Os campos extraídos pelo parser incluem posto, nome recebido, horário de assunção e data, conforme o conteúdo da mensagem.

O relatório retorna `ok`, o plantão selecionado, totais da escala e de registros identificados, contadores por situação e a lista `results` com os detalhes classificados.

## Fluxo e arquitetura

```text
Cliente WhatsApp opcional ──POST──▶ FastAPI (app/main.py)
                                          │
                                  parser.py / compare.py
                                          │
                                     matcher.py
                                          │
                              escala e mensagens em JSON
                                          │
                                 dashboard HTML / API
```

- `app/parser.py` interpreta mensagens não estruturadas.
- `app/compare.py` compara os campos extraídos com a escala.
- `app/matcher.py` monta o relatório de acordo com posto, plantão, data e similaridade textual.
- `app/storage.py` lê e grava mensagens em `data/messages.json`.
- `app/main.py` expõe as rotas FastAPI e renderiza os templates.

## Estrutura do repositório

```text
ControlOps/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── main_backup.py
│   ├── compare.py
│   ├── matcher.py
│   ├── parser.py
│   ├── storage.py
│   ├── static/
│   │   └── .gitkeep
│   └── templates/
│       ├── dashboard.html
│       ├── dashboard-html.txt
│       └── test.html
├── data/
│   ├── aliases.json
│   ├── escala.json
│   └── messages.json
├── tests/
│   ├── generate_messages.py
│   ├── test_parser.py
│   └── test_parser_unit.py
├── whatsapp/
│   └── client.js
├── .gitignore
├── README.md
├── README_INTEGRACAO.md
├── converter_escala.py
├── package.json
├── package-lock.json
└── requirements.txt
```

`converter_escala.py` é um utilitário que altera `data/escala.json` para duas datas específicas; revise o arquivo antes de executá-lo. `main_backup.py` e `dashboard-html.txt` são cópias/rascunhos presentes no repositório, não os componentes usados pela aplicação ativa.

## Dados e limitações conhecidas

- A aplicação usa arquivos JSON locais, sem banco de dados ou histórico transacional.
- Não há rota de leitura `GET /api/messages` na aplicação atual.
- A escala e os aliases são carregados de arquivos em `data/`; ajuste-os ao ambiente de teste antes de uso.
- Os arquivos `data/escala.json`, `data/aliases.json` e `data/messages.json` contêm dados fictícios de demonstração. Se forem substituídos por dados reais para uso local, não os redistribua sem sanitização.
- A pasta `app/static/` está preparada, mas não contém os ativos de imagem citados em documentos antigos.
- O cliente WhatsApp imprime mensagens no terminal e depende de sessão local do WhatsApp Web.
- A classificação depende dos formatos reconhecidos pelo parser e da qualidade da escala cadastrada.

## Roadmap

Itens planejados, ainda não implementados:

- migrar o armazenamento JSON para banco de dados;
- registrar histórico e logs estruturados de processamento;
- ampliar indicadores e análises históricas;
- adicionar monitoramento e validação do pipeline.
