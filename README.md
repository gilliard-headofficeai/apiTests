# API Tests — Wrapper, cache e dashboard

Projeto que atua como **proxy** da API real de relatórios: chama o backend, persiste o JSON bruto e otimizado em cache, gera relatórios de comparação e expõe métricas tratadas para o dashboard (Visão Geral).

## O que este projeto faz

1. **Wrapper HTTP** — Recebe `GET /wrapper/report_lia?from=&to=` e repassa à API real (porta 3000) com parâmetros fixos (agentId, etc.) do `.env` e `config/api_endpoints.json`. **Resposta padrão:** JSON tratado para dashboards (visao_geral, etc.). Com `?view=full` devolve o JSON otimizado completo (relatório).
2. **Cache** — Salva em disco o JSON bruto, o otimizado, o tratado para dashboard e os relatórios de comparação: `raw_liareport.json`, `optimized_liareport.json`, `dashboard_liareport.json`, `comparison_liareport.md/.html/.json`. Cada nova chamada substitui os arquivos do mesmo endpoint.
3. **Otimização** — Reduz redundância: consolida chaves pt→en em `dataCollectFromUser`, normaliza `sender` para `"agent"`/`"user"`, move o agente para `meta.agent` e remove `aiAgent`/`agentId` vazio de cada item.
4. **Comparação** — Gera relatório (Markdown, HTML lado a lado e JSON de métricas) entre resposta bruta e otimizada.
5. **Dashboard** — A partir do JSON otimizado, calcula métricas da Visão Geral (total de conversas, mensagens da LIA, distribuição por estado, faixa etária, atendimentos por hora, etc.) para consumo pelo front em uma única API.

## Estrutura do projeto

```
apiTests/
├── main.py                 # Sobe o servidor wrapper; ngrok em outro terminal ou use --ngrok
├── src/
│   ├── config.py           # BASE_URL, CACHE_DIR, WRAPPER_PORT, api_endpoints.json, slug por endpoint
│   ├── api_client.py       # GET na API real com X-API-Key e query params
│   ├── storage.py          # Pasta de cache por endpoint; save raw/optimized com nome curto (slug)
│   ├── optimizer.py        # Otimização do JSON (dataCollectFromUser, sender, meta.agent)
│   ├── wrapper_server.py   # FastAPI: /wrapper/{endpoint_key} → fetch, save, optimize, compare, return
│   ├── compare_report.py   # Comparação raw vs optimized; gera .md, .html, .json de métricas
│   └── dashboard_treatments.py  # build_visao_geral / build_dashboard_payload a partir do otimizado
├── config/
│   └── api_endpoints.json  # Chave → path e default_params (agentId, by, messageHistory)
├── cache/                  # Por endpoint (ex.: report_lia/): raw_*, optimized_*, dashboard_*, comparison_*
├── tests/
│   └── fixtures/           # Ex.: optimized_liareport_sample.json para testes do dashboard
└── docs/                   # Guias (Postman, configuração front/dashboard)
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

- **Um comando (recomendado):**
  `python main.py`
  Abre o ngrok em uma **nova janela** (CMD no Windows) e sobe o servidor **neste terminal**. Os logs das chamadas aparecem aqui; a URL HTTPS fica na janela do ngrok.

- **Só o servidor (sem abrir ngrok):**
  `python main.py --no-ngrok`
  `uvicorn src.wrapper_server:app --host 0.0.0.0 --port 8000`

- **Relatório de comparação a partir do cache:**  
  `python -m src.compare_report report_lia`  
  (usa o par raw/optimized mais recente)  
  Com parâmetros: `python -m src.compare_report report_lia --from 2026-01-01 --to 2026-01-14`

- **Teste do dashboard (métricas da Visão Geral):**  
  `python -m src.dashboard_treatments`  
  (carrega o optimized mais recente do cache para `report_lia`)  
  Ou com arquivo: `python -m src.dashboard_treatments --file path/to/optimized_liareport.json`

## Padrão de nomes no cache

Nomes curtos por endpoint (um arquivo de cada tipo por endpoint; cada chamada substitui):

- **raw_&lt;slug&gt;.json** — Resposta bruta da API (ex.: `raw_liareport.json`)
- **optimized_&lt;slug&gt;.json** — Resposta após otimização (ex.: `optimized_liareport.json`)
- **dashboard_&lt;slug&gt;.json** — JSON tratado para dashboards (visao_geral, etc.), igual à resposta padrão do wrapper
- **comparison_&lt;slug&gt;.md / .html / .json** — Relatório de comparação e métricas

O **slug** vem de `config.ENDPOINT_SLUGS` (ex.: `report_lia` → `liareport`). Padrão reutilizável para outras soluções.

## Fluxo de uma requisição

1. Cliente chama `GET /wrapper/report_lia?from=2026-01-01&to=2026-01-14`.
2. **wrapper_server** resolve o endpoint, monta params (default_params + query), chama **api_client** para obter o JSON bruto da API real.
3. **storage** salva o bruto em `cache/report_lia/raw_liareport.json`.
4. **optimizer** processa o JSON e **storage** salva em `optimized_liareport.json`.
5. **compare_report** gera e salva os relatórios de comparação (comparison_liareport.md, etc.).
6. **Resposta padrão:** payload tratado para dashboard (visao_geral) é salvo em `dashboard_liareport.json` e devolvido ao cliente.
6. O servidor devolve o JSON otimizado ao cliente.

Para o dashboard, o front pode (futuramente) chamar uma rota que carrega o otimizado (do cache ou da última resposta) e aplica **dashboard_treatments.build_dashboard_payload**, devolvendo um único JSON com chaves por página (ex.: `visao_geral`).

## Documentação adicional

- **docs/postman-report-lia.md** — Como testar o endpoint Report Lia no Postman e com ngrok.
- **docs/lovable-config-guide.md** — Guia de configuração da API de relatório para o front/dashboard (URL placeholder, campos Visão Geral, remoção de menções a ferramentas).

## Resumo por arquivo (para leitura humana)

- **main.py** — Ponto de entrada: um comando abre o ngrok em outra janela e sobe o servidor neste terminal (logs aqui); `--no-ngrok` sobe só o servidor.
- **src/config.py** — Lê `.env` e `config/api_endpoints.json`; expõe BASE_URL, CACHE_DIR, WRAPPER_PORT, GENERAL_REPORT_API_KEY, e funções para path e slug por endpoint.
- **src/api_client.py** — Faz GET na API real (BASE_URL + path), com query params e header X-API-Key; retorna o JSON.
- **src/storage.py** — Define a pasta de cache por endpoint e salva raw/optimized/dashboard (raw_&lt;slug&gt;.json, optimized_&lt;slug&gt;.json, dashboard_&lt;slug&gt;.json).
- **src/optimizer.py** — Transforma o JSON do report: dataCollectFromUser pt→en, sender → "agent"/"user", meta.agent no topo, remove aiAgent e agentId vazio.
- **src/wrapper_server.py** — FastAPI com rota GET /wrapper/{endpoint_key}; orquestra fetch → save raw → optimize → save optimized → run_comparison → return optimized.
- **src/compare_report.py** — Localiza par raw/optimized no cache (por params ou par mais recente), compara, gera Markdown/HTML/JSON e salva comparison_&lt;slug&gt;.*.
- **src/dashboard_treatments.py** — A partir do JSON otimizado, calcula total_conversas, mensagens_lia, distribuição por estado, faixa etária, menores_de_18, atendimentos_por_hora, etc., e retorna o payload da visão_geral (e futuras páginas) para o front.
