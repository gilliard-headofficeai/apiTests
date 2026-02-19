"""
Cliente da API real: monta URL a partir de base + path e executa GET com query params.
A API real exige o header X-API-Key; o valor vem de GENERAL_REPORT_API_KEY no .env.
Responsabilidade: única camada que faz HTTP para o backend; usado pelo wrapper_server.
"""
import requests
from src.config import BASE_URL, GENERAL_REPORT_API_KEY, resolve_path


def _default_headers() -> dict:
    """Headers enviados em toda chamada à API real. API real espera X-API-Key com GENERAL_REPORT_API_KEY."""
    headers = {"Accept": "application/json"}
    if GENERAL_REPORT_API_KEY:
        headers["X-API-Key"] = GENERAL_REPORT_API_KEY
    return headers


def fetch_json(
    endpoint_key_or_path: str,
    params: dict | None = None,
    timeout: int = 60,
) -> dict:
    """
    Chama a API real e retorna o JSON da resposta.
    endpoint_key_or_path: chave do api_endpoints.json (ex: report_agent) ou path (ex: v1/convesation/...).
    params: query string (by, messageHistory, agentId, from, to, etc.).
    A chave GENERAL_REPORT_API_KEY (.env) é enviada no header X-API-Key.
    """
    path = resolve_path(endpoint_key_or_path)
    if path is None:
        raise ValueError(f"Endpoint não encontrado: {endpoint_key_or_path}")
    url = f"{BASE_URL}/{path}"
    # No Windows, cliente não pode conectar em 0.0.0.0 — garantir localhost
    if "0.0.0.0" in url:
        url = url.replace("0.0.0.0", "localhost")
    resp = requests.get(
        url,
        params=params or {},
        headers=_default_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()
