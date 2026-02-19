"""
Servidor HTTP (FastAPI) que expõe rotas /wrapper/{endpoint_key}.
Repassa query params à API real, salva bruto, otimiza e devolve JSON otimizado.
Arquivos no cache usam o padrão slug + timestamp (ex.: optimized_liareport_20260219_143022.json).
Responsabilidade: orquestrar uma requisição (fetch -> save raw -> optimize -> save optimized -> run_comparison -> return); ponto de entrada HTTP do projeto.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.config import get_endpoint_config, load_endpoints, WRAPPER_PORT
from src.api_client import fetch_json
from src.storage import save_raw, save_optimized
from src.optimizer import optimize_report_response
from src.compare_report import run_comparison

app = FastAPI(
    title="Wrapper API Report",
    description="Proxy que chama a API real, persiste o bruto e devolve JSON otimizado.",
)


@app.get("/wrapper/{endpoint_key}")
async def wrapper_get(endpoint_key: str, request: Request):
    """
    Rota encurtada: GET /wrapper/report_lia?from=2026-01-01&to=2026-01-14
    O frontend envia só o que o usuário escolhe (ex.: período). Parâmetros sensíveis
    (agentId, by, messageHistory) vêm de default_params no config e não são expostos.
    """
    config = get_endpoint_config(endpoint_key)
    if not config:
        endpoints = load_endpoints()
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint desconhecido: {endpoint_key}. Chaves disponíveis: {list(endpoints.keys())}",
        )
    # Parâmetros fixos do backend (ex.: agentId) + query do frontend (ex.: from, to)
    query_params = dict(request.query_params)
    params = {**config.get("default_params", {}), **query_params}
    try:
        raw = fetch_json(endpoint_key, params=params)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao chamar API real: {e}") from e
    # Usar "latest" para substituir o cache a cada nova chamada do mesmo endpoint
    save_raw(endpoint_key, raw, params=params, timestamp="latest")
    optimized = optimize_report_response(raw)
    save_optimized(endpoint_key, optimized, params=params, timestamp="latest")
    run_comparison(endpoint_key, params, raw=raw, optimized=optimized, timestamp="latest")
    return JSONResponse(
        content=optimized,
        headers={"X-Wrapper-Optimized": "true"},
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
