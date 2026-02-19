# API Tests — Wrapper, cache e dashboard

Projeto que atua como **proxy** da API real de relatórios: chama o backend, persiste o JSON bruto e otimizado em cache, gera relatórios de comparação e expõe métricas tratadas para o dashboard (Visão Geral).

## O que este projeto faz

1. **Wrapper HTTP** — Recebe `GET /wrapper/report_lia?from=&to=` e repassa à API real (porta 3000) com parâmetros fixos (agentId, etc.) do `.env` e `config/api_endpoints.json`. Resposta é otimizada e devolvida ao cliente.
2. **Cache** — Salva em disco o JSON bruto e o otimizado (e opcionalmente relatórios de comparação) com nomes padronizados: `raw_liareport_<timestamp>.json`, `optimized_liareport_<timestamp>.json`, `comparison_liareport_<timestamp>.md/.html/.json`.
3. **Otimização** — Reduz redundância: consolida chaves pt→en em `dataCollectFromUser`, normaliza `sender` para `"agent"`/`"user"`, move o agente para `meta.agent` e remove `aiAgent`/`agentId` vazio de cada item.
4. **Comparação** — Gera relatório (Markdown, HTML lado a lado e JSON de métricas) entre resposta bruta e otimizada.
5. **Dashboard** — A partir do JSON otimizado, calcula métricas da Visão Geral (total de conversas, mensagens da LIA, distribuição por estado, faixa etária, atendimentos por hora, etc.) para consumo pelo front em uma única API.

## Estrutura do projeto

```
apiTests/
├── main.py                 # Sobe o servidor wrapper e inicia ngrok (um comando só)
├── src/
│   ├── config.py           # BASE_URL, CACHE_DIR, WRAPPER_PORT, api_endpoints.json, slug por endpoint
│   ├── api_client.py       # GET na API real com X-API-Key e query params
│   ├── storage.py          # Pasta de cache por endpoint; save raw/optimized com slug_timestamp
│   ├── optimizer.py        # Otimização do JSON (dataCollectFromUser, sender, meta.agent)
│   ├── wrapper_server.py   # FastAPI: /wrapper/{endpoint_key} → fetch, save, optimize, compare, return
│   ├── compare_report.py   # Comparação raw vs optimized; gera .md, .html, .json de métricas
│   └── dashboard_treatments.py  # build_visao_geral / build_dashboard_payload a partir do otimizado
├── config/
│   └── api_endpoints.json  # Chave → path e default_params (agentId, by, messageHistory)
├── cache/                  # Por endpoint (ex.: report_lia/): raw_*, optimized_*, comparison_*
├── tests/
│   └── fixtures/           # Ex.: optimized_liareport_sample.json para testes do dashboard
└── docs/                   # Guias (Postman, Lovable, etc.)
```

## Variáveis de ambiente

Crie um `.env` na raiz do projeto (ou use as variáveis no ambiente):

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `WRAPPER_BASE_URL` | URL da API real | `http://localhost:3000` |
| `GENERAL_REPORT_API_KEY` | Chave enviada no header `X-API-Key` para a API real | (valor secreto) |
| `WRAPPER_CACHE_DIR` | Pasta raiz do cache | `./cache` (default) |
| `WRAPPER_PORT` | Porta do servidor wrapper | `8000` |

No Windows, use `localhost` em `WRAPPER_BASE_URL` (não `0.0.0.0`).

## Como rodar

- **Servidor + ngrok (um comando):**  
  `python main.py`  
  Servidor em `http://localhost:8000`; ngrok expõe a URL HTTPS para uso no Lovable.

- **Só o servidor (sem ngrok):**  
  `uvicorn src.wrapper_server:app --host 0.0.0.0 --port 8000`

- **Relatório de comparação a partir do cache:**  
  `python -m src.compare_report report_lia`  
  (usa o par raw/optimized mais recente)  
  Com parâmetros: `python -m src.compare_report report_lia --from 2026-01-01 --to 2026-01-14`

- **Teste do dashboard (métricas da Visão Geral):**  
  `python -m src.dashboard_treatments`  
  (carrega o optimized mais recente do cache para `report_lia`)  
  Ou com arquivo: `python -m src.dashboard_treatments --file path/to/optimized_liareport_*.json`

## Padrão de nomes no cache

Para facilitar reutilização em outras soluções, os arquivos usam um padrão curto:

- **raw_&lt;slug&gt;_&lt;timestamp&gt;.json** — Resposta bruta da API (ex.: `raw_liareport_20260219_143022.json`)
- **optimized_&lt;slug&gt;_&lt;timestamp&gt;.json** — Resposta após otimização
- **comparison_&lt;slug&gt;_&lt;timestamp&gt;.md / .html / .json** — Relatório de comparação e métricas

O **slug** vem de `config.ENDPOINT_SLUGS` (ex.: `report_lia` → `liareport`). O **timestamp** é `YYYYMMDD_HHMMSS` (UTC) no momento da gravação. Cada requisição ao wrapper gera um novo par raw/optimized com o mesmo timestamp, e o compare_report grava os arquivos de comparação com esse mesmo timestamp.

## Fluxo de uma requisição

1. Cliente chama `GET /wrapper/report_lia?from=2026-01-01&to=2026-01-14`.
2. **wrapper_server** resolve o endpoint, monta params (default_params + query), chama **api_client** para obter o JSON bruto da API real.
3. **storage** salva o bruto em `cache/report_lia/raw_liareport_<ts>.json`.
4. **optimizer** processa o JSON e **storage** salva em `optimized_liareport_<ts>.json`.
5. **compare_report** gera e salva os relatórios de comparação com o mesmo `<ts>`.
6. O servidor devolve o JSON otimizado ao cliente.

Para o dashboard, o front pode (futuramente) chamar uma rota que carrega o otimizado (do cache ou da última resposta) e aplica **dashboard_treatments.build_dashboard_payload**, devolvendo um único JSON com chaves por página (ex.: `visao_geral`).

## Documentação adicional

- **docs/postman-report-lia.md** — Como testar o endpoint Report Lia no Postman e com ngrok no Lovable.
- **docs/lovable-config-guide.md** — Configuração do Lovable para usar o wrapper.

## Resumo por arquivo (para leitura humana)

- **main.py** — Ponto de entrada: inicia o servidor em thread e executa `ngrok http 8000` para expor o wrapper.
- **src/config.py** — Lê `.env` e `config/api_endpoints.json`; expõe BASE_URL, CACHE_DIR, WRAPPER_PORT, GENERAL_REPORT_API_KEY, e funções para path e slug por endpoint.
- **src/api_client.py** — Faz GET na API real (BASE_URL + path), com query params e header X-API-Key; retorna o JSON.
- **src/storage.py** — Define a pasta de cache por endpoint, gera o sufixo dos arquivos (slug_timestamp ou params) e salva raw/optimized.
- **src/optimizer.py** — Transforma o JSON do report: dataCollectFromUser pt→en, sender → "agent"/"user", meta.agent no topo, remove aiAgent e agentId vazio.
- **src/wrapper_server.py** — FastAPI com rota GET /wrapper/{endpoint_key}; orquestra fetch → save raw → optimize → save optimized → run_comparison → return optimized.
- **src/compare_report.py** — Localiza par raw/optimized no cache (por params ou par mais recente), compara, gera Markdown/HTML/JSON de métricas e salva com nome comparison_<slug>_<timestamp>.
- **src/dashboard_treatments.py** — A partir do JSON otimizado, calcula total_conversas, mensagens_lia, distribuição por estado, faixa etária, menores_de_18, atendimentos_por_hora, etc., e retorna o payload da visão_geral (e futuras páginas) para o front.
