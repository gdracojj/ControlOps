# Integração opcional com WhatsApp

O cliente em `whatsapp/client.js` usa `whatsapp-web.js` para receber mensagens de grupos e encaminhá-las à API local do ControlOps (`POST http://127.0.0.1:8000/api/messages`). A integração é opcional; a API e o dashboard podem ser executados sem Node.js.

## Pré-requisitos

- API ControlOps iniciada conforme o [README principal](README.md);
- Node.js e npm instalados;
- um WhatsApp para autenticar a sessão pelo QR Code.

## Configuração e início

1. Edite `MONITORED_GROUPS` em `whatsapp/client.js` e informe os IDs dos grupos autorizados.
2. Instale as dependências na raiz do repositório e inicie o cliente:

```bash
npm ci
node whatsapp/client.js
```

3. Leia o QR Code exibido no terminal com o WhatsApp. A sessão é mantida localmente por `LocalAuth`.

**Atenção:** com `MONITORED_GROUPS` vazio, o cliente aceita mensagens de todos os grupos. O cliente também imprime o conteúdo recebido no terminal. Configure e execute apenas em um ambiente autorizado, sem dados que não devam ser processados ou registrados localmente.

## Limitações

- A URL da API está fixa em `http://127.0.0.1:8000/api/messages` no código.
- O cliente observa eventos de novas mensagens; não importa histórico anterior.
- O envio é feito mensagem a mensagem e não há fila ou mecanismo de repetição persistente.
- A pasta `app/static/` não contém a logo citada em documentos anteriores. A aplicação não inclui esse arquivo de imagem.
