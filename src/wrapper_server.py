"""
Servidor HTTP (FastAPI) que expõe rotas /wrapper/{endpoint_key}.
Repassa query params à API real, salva bruto, otimiza e devolve JSON otimizado.
Arquivos no cache: raw_<slug>.json, optimized_<slug>.json e dashboard_<slug>.json; cada chamada substitui.
Responsabilidade: orquestrar uma requisição (fetch -> save raw -> optimize -> save optimized -> run_comparison -> return); ponto de entrada HTTP do projeto.
"""
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_endpoint_config, load_endpoints, WRAPPER_PORT
from src.api_client import fetch_json
from src.storage import save_raw, save_optimized, save_dashboard
from src.optimizer import optimize_report_response
from src.compare_report import run_comparison
from src.dashboard_treatments import (
    build_dashboard_payload,
    build_visao_geral,
    build_comparativo_mes_anterior,
)

app = FastAPI(
    title="Wrapper API Report",
    description="Proxy que chama a API real, persiste o bruto e devolve por padrão o JSON tratado para dashboards (visao_geral, etc.).",
)

# CORS: front (ex.: Lovable) em outro domínio faz preflight OPTIONS antes do GET; sem isso retorna 405
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/wrapper/{endpoint_key}")
async def wrapper_get(endpoint_key: str, request: Request):
    """
    Rota encurtada: GET /wrapper/report_lia?from=2026-01-01&to=2026-01-14
    Resposta padrão: JSON tratado para dashboards (visao_geral, etc.), pronto para o front.
    Com ?view=full devolve o JSON otimizado completo (relatório bruto tratado).
    """
    config = get_endpoint_config(endpoint_key)
    if not config:
        endpoints = load_endpoints()
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint desconhecido: {endpoint_key}. Chaves disponíveis: {list(endpoints.keys())}",
        )
    query_params = dict(request.query_params)
    view_full = query_params.pop("view", None) == "full"
    compare_previous_month = query_params.pop("compare", None) == "previous_month"
    params = {**config.get("default_params", {}), **query_params}
    try:
        raw = fetch_json(endpoint_key, params=params)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao chamar API real: {e}") from e
    save_raw(endpoint_key, raw, params=params, timestamp="latest")
    optimized = optimize_report_response(raw)
    save_optimized(endpoint_key, optimized, params=params, timestamp="latest")
    run_comparison(endpoint_key, params, raw=raw, optimized=optimized, timestamp="latest")
    if view_full:
        return JSONResponse(
            content=optimized,
            headers={"X-Wrapper-View": "full"},
        )
    payload = build_dashboard_payload(optimized)
    if compare_previous_month and params.get("from"):
        try:
            from_str = params["from"]
            d = date.fromisoformat(from_str)
            first_curr = d.replace(day=1)
            prev_end = first_curr - timedelta(days=1)
            prev_start = prev_end.replace(day=1)
            params_anterior = {**params, "from": prev_start.isoformat(), "to": prev_end.isoformat()}
            raw_anterior = fetch_json(endpoint_key, params=params_anterior)
            optimized_anterior = optimize_report_response(raw_anterior)
            visao_atual = payload["visao_geral"]
            visao_anterior = build_visao_geral(optimized_anterior)
            payload["comparativo_mes_anterior"] = build_comparativo_mes_anterior(visao_atual, visao_anterior)
        except (ValueError, KeyError) as e:
            payload["comparativo_mes_anterior"] = None
    save_dashboard(endpoint_key, payload, params=params, timestamp="latest")
    return JSONResponse(
        content=payload,
        headers={"X-Wrapper-View": "dashboard"},
    )


def serve(port: int | None = None):
    """Sobe o servidor uvicorn."""
    import uvicorn
    uvicorn.run(
        "src.wrapper_server:app",
        host="0.0.0.0",
        port=port or WRAPPER_PORT,
        reload=False,
    )
