# ControlOps

Aplicação Python com API FastAPI para interpretar mensagens de assunção de serviço e compará-las com uma escala operacional.

## Problema e funcionalidades

Mensagens operacionais podem chegar em texto livre, com horários, postos e nomes em formatos diferentes. O ControlOps extrai os campos reconhecidos, compara-os com a escala configurada e apresenta os resultados em uma API e em um dashboard.

O repositório implementa:

- extração de posto, colaborador, horário e data pelo parser;
- normalização e comparação textual de nomes e postos;
- correspondência com escala por plantão e paridade do dia;
- classificação de horários e identificação de postos sem assunção;
- API FastAPI, dashboard HTML e armazenamento local em JSON;
- cliente opcional Node.js para encaminhar mensagens de grupos do WhatsApp;
- gerador de mensagens e testes do parser.

A integração com WhatsApp requer configuração própria. A lista de grupos monitorados está vazia por padrão; nesse estado, o cliente encaminha mensagens de todos os grupos. Configure a lista antes de iniciar o cliente.

## Requisitos

- Python 3.10 ou superior;
- Node.js e npm apenas para usar o cliente opcional do WhatsApp;
- dependências Python listadas em requirements.txt.

## Stack

- Python, FastAPI, Pydantic, Jinja2 e RapidFuzz;
- HTML, CSS e JavaScript no dashboard;
- JSON para escala, aliases e armazenamento local;
- Node.js, whatsapp-web.js e qrcode-terminal para a integração opcional.

## Instalação e execução

Na raiz do repositório, em Linux ou macOS:

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

No Windows PowerShell:

py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

A aplicação fica disponível em http://127.0.0.1:8000.

Para usar o cliente opcional do WhatsApp, configure os grupos autorizados em MONITORED_GROUPS, inicie a API e execute, na raiz do repositório:

npm ci
node whatsapp/client.js

O cliente solicita autenticação pelo QR Code e encaminha as mensagens para http://127.0.0.1:8000/api/messages.

## Testes

Gere o conjunto local de mensagens e execute o teste de parser:

python tests/generate_messages.py
python tests/test_parser.py

Os testes unitários em tests/test_parser_unit.py usam pytest. Instale-o no ambiente e execute:

python -m pip install pytest
python -m pytest -q

O gerador cria data/test_messages_1000.json e o teste grava data/parser_failures.json. Ambos são artefatos locais ignorados pelo Git.

## API e formato de entrada

- GET / — dashboard;
- GET /api/report?plantao=diurno_a — relatório do plantão (diurno_a, noturno_a, diurno_b ou noturno_b);
- POST /api/messages — recebe e processa uma mensagem;
- POST /api/refresh — substitui o conjunto de mensagens pelo lote enviado;
- POST /api/clear — limpa o armazenamento local;
- GET /teste — página de testes da interface.

O corpo esperado por POST /api/messages é:

{
  "group": "ID_DO_GRUPO",
  "message": "texto da mensagem operacional",
  "received_at": "2026-10-25T06:00:00"
}

group e received_at são opcionais; message é obrigatório. O parser extrai campos como posto, nome recebido, horário de assunção e data, conforme o conteúdo da mensagem.

O relatório inclui o plantão selecionado, totais da escala e de registros identificados, contadores por situação e a lista results com os detalhes classificados.

## Fluxo e arquitetura

Cliente WhatsApp opcional ──POST──▶ FastAPI (app/main.py)
                                          │
                                  parser.py / compare.py
                                          │
                                     matcher.py
                                          │
                              escala e mensagens em JSON
                                          │
                                 dashboard HTML / API

- app/parser.py interpreta mensagens não estruturadas.
- app/compare.py compara os campos extraídos com a escala.
- app/matcher.py monta o relatório de acordo com posto, plantão, data e similaridade textual.
- app/storage.py lê e grava mensagens em data/messages.json.
- app/main.py expõe as rotas FastAPI e renderiza os templates.

## Estrutura do repositório

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

main_backup.py e dashboard-html.txt são cópias ou rascunhos presentes no repositório, não os componentes usados pela aplicação ativa.

converter_escala.py é um utilitário legado que procura registros com date igual a 2026-09-25 ou 2026-09-26 para ajustar o plantão. Os 60 registros atuais de data/escala.json não têm o campo date; portanto, o script não altera os valores de plantão, embora regrave o JSON.

## Dados e limitações conhecidas

- A aplicação usa arquivos JSON locais, sem banco de dados ou histórico transacional.
- Não há rota de leitura GET /api/messages na aplicação atual.
- A escala e os aliases são carregados de arquivos em data/.
- Os arquivos atuais de escala, aliases e mensagens contêm dados fictícios de demonstração.
- A pasta app/static/ está preparada, mas não contém ativos de imagem.
- O cliente WhatsApp imprime mensagens no terminal e depende de uma sessão local do WhatsApp Web.
- A classificação depende dos formatos reconhecidos pelo parser e da qualidade da escala cadastrada.

## Aprendizados

O desenvolvimento do ControlOps aborda problemas comuns no processamento de dados operacionais, como mensagens incompletas, formatos de horário variados, normalização de nomes, identificação de entidades e rastreabilidade.

## Princípios

- Separação entre interpretação, comparação, matching, armazenamento e apresentação.
- Regras de negócio explícitas e testáveis.
- Uso de dados fictícios para demonstração.
- Evolução incremental da aplicação e da camada de dados.

## Status

Em desenvolvimento. O projeto já inclui parser, comparação com escala, API, armazenamento JSON, dashboard, integração opcional com WhatsApp e testes do parser. A migração do armazenamento, o histórico estruturado e a ampliação dos indicadores permanecem no roadmap.

## Autor e propósito

Gabriel Silva

Projeto desenvolvido para fins educacionais e de portfólio, com foco prático em Data Engineering, Data Analytics, Python, APIs e automação.
