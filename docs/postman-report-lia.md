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

Não é necessário enviar header de API key no Postman: o wrapper usa `GENERAL_REPORT_API_KEY` do `.env` ao chamar a API real.

**Resposta padrão:** o wrapper devolve o JSON **tratado para dashboards** (ex.: `visao_geral` com total_conversas, mensagens_lia, etc.), pronto para o front.  
Para receber o relatório otimizado completo, use **`view=full`** na query.

Exemplo (resposta = dashboard tratado):
```
GET http://localhost:8000/wrapper/report_lia?from=2026-01-01&to=2026-01-14
```
Relatório completo (quando precisar):
```
GET http://localhost:8000/wrapper/report_lia?from=2026-01-01&to=2026-01-14&view=full
```

### Arquivos no cache (conferência local)

Após cada chamada ao wrapper, na pasta `cache/report_lia/` ficam salvos:

| Arquivo | Conteúdo |
|---------|----------|
| `raw_liareport.json` | Resposta bruta da API real |
| `optimized_liareport.json` | Relatório otimizado (estrutura completa) |
| **`dashboard_liareport.json`** | **JSON tratado para dashboards** — igual à resposta padrão do wrapper (visao_geral, etc.). Use para conferir localmente o que o Postman ou o front recebem. |
| `comparison_liareport.md` / `.html` / `.json` | Relatórios de comparação raw vs otimizado |

Exemplo com ngrok (mesma resposta tratada):
```
GET https://<sua-url-ngrok>.ngrok-free.dev/wrapper/report_lia?from=2026-01-01&to=2026-02-19
```
A resposta (visao_geral, distribuição por estado, faixa etária, atendimentos por hora, etc.) fica também em `cache/report_lia/dashboard_liareport.json`.

---

## Testar com ngrok (front em outro host)

1. **Um comando só:** na pasta do projeto rode:
   ```bash
   python main.py
   ```
   Isso abre o **ngrok em uma nova janela** (CMD no Windows) e sobe o **servidor neste terminal**. Os logs das chamadas aparecem neste terminal; a URL HTTPS aparece na janela do ngrok.
2. Na janela do ngrok será impressa a **URL pública** (ex.: `https://abc123.ngrok-free.app`). Use-a no front (variável de ambiente ou config; não hardcodar).
3. Exemplo de chamada para o front (substitua pela sua URL ngrok):
   ```
   GET https://<sua-url>.ngrok-free.app/wrapper/report_lia?from=2026-01-01&to=2026-01-14
   ```
4. No front: configure a base URL do relatório como placeholder (ex.: variável de ambiente) apontando para a URL do ngrok e o path `/wrapper/report_lia`; envie só `from` e `to` no período.

### Exemplo com URL real (ngrok)

| Uso | Valor |
|-----|--------|
| **Base URL (exemplo dev)** | Use placeholder; ex. ngrok: `https://xxxx.ngrok-free.dev` |
| **Path do relatório** | `/wrapper/report_lia` |
| **Chamada completa (GET)** | `https://<sua-url-ngrok>.ngrok-free.dev/wrapper/report_lia?from=YYYY-MM-DD&to=YYYY-MM-DD` (substituir por placeholder em produção) |

No front: use a base URL em variável de ambiente (substituível por produção); ao mudar o período, monte a query com `from` e `to` (YYYY-MM-DD). Não é necessário enviar header `X-API-Key`; o wrapper adiciona isso ao chamar a API real.

**Requisito:** ngrok instalado e configurado com authtoken (`ngrok config add-authtoken <seu-token>`). Com `python main.py` o ngrok abre em outra janela automaticamente; para só o servidor use `python main.py --no-ngrok` e rode o ngrok manualmente em outro terminal se precisar.

---

## Resumo das portas

| Serviço | Porta | URL base |
|---------|-------|----------|
| API real (backend) | 3000 | `http://localhost:3000` |
| Wrapper (nosso) | 8000 | `http://localhost:8000` |
| Ngrok (túnel) | 8000 → HTTPS | Ex.: `https://xxxx.ngrok.io` |
