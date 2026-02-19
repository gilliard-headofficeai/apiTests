# Testar endpoint Report Lia no Postman

## Pré-requisitos

1. **API real** rodando na porta **3000** (backend que devolve o relatório bruto).
2. **Wrapper** rodando na porta **8000**:
   ```bash
   cd C:\HeadOfficeAi\apiTests
   python main.py
   ```
3. `.env` com `GENERAL_REPORT_API_KEY` e `WRAPPER_BASE_URL=http://localhost:3000` (no Windows use `localhost`, não `0.0.0.0`).

---

## Endpoint no Postman

| Campo | Valor |
|-------|--------|
| **Método** | `GET` |
| **URL** | `http://localhost:8000/wrapper/report_lia` |
| **Query params** | Apenas o que o front envia (período). O backend adiciona `agentId`, `by`, `messageHistory`. |

### Parâmetros de query (você envia no Postman)

| Parâmetro | Obrigatório | Exemplo | Descrição |
|-----------|-------------|---------|-----------|
| `from` | Sim | `2026-01-01` | Data início (YYYY-MM-DD). |
| `to` | Sim | `2026-01-14` | Data fim (YYYY-MM-DD). |

### Exemplo de URL completa no Postman

```
GET http://localhost:8000/wrapper/report_lia?from=2026-01-01&to=2026-01-14
```

Não é necessário enviar header de API key no Postman: o wrapper usa `GENERAL_REPORT_API_KEY` do `.env` ao chamar a API real. A resposta é o JSON **otimizado** (menos linhas, `sender` como `agent`/`user`, `meta.agent` no topo).

---

## Testar com ngrok (front em outro host, ex.: Lovable)

1. Subir o wrapper com **um comando** (já inicia servidor + ngrok):
   ```bash
   python main.py
   ```
2. No console será impressa a **URL pública do ngrok** (ex.: `https://abc123.ngrok-free.app`). Use-a no Lovable.
3. Exemplo de chamada para o front:
   ```
   GET https://<sua-url>.ngrok-free.app/wrapper/report_lia?from=2026-01-01&to=2026-01-14
   ```
4. No Lovable: configure a base URL do relatório como `https://<sua-url>.ngrok-free.app` e o path como `/wrapper/report_lia`; envie só `from` e `to` no período.

**Requisito:** ngrok configurado com authtoken (`ngrok config add-authtoken <seu-token>`).

---

## Resumo das portas

| Serviço | Porta | URL base |
|---------|-------|----------|
| API real (backend) | 3000 | `http://localhost:3000` |
| Wrapper (nosso) | 8000 | `http://localhost:8000` |
| Ngrok (túnel) | 8000 → HTTPS | Ex.: `https://xxxx.ngrok.io` |
