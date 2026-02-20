"""
Persistência local: cria pasta por endpoint (chave ou path normalizado) e salva JSON bruto, otimizado e dashboard.
Nomes: raw_<slug>.json, optimized_<slug>.json, dashboard_<slug>.json (ex.: raw_liareport.json, optimized_liareport.json, dashboard_liareport.json).
Cada nova chamada substitui os arquivos do mesmo endpoint. Padrão reutilizável para outras soluções.
Responsabilidade: definir onde e com que nome os arquivos são gravados; usado pelo wrapper e pelo compare_report.
"""
import json
import re
from pathlib import Path
from datetime import datetime

from src.config import CACHE_DIR, resolve_path, get_endpoint_slug


def _normalize_for_folder(name: str) -> str:
    """Normaliza string para uso como nome de pasta (sem barras, caracteres seguros)."""
    s = name.strip().strip("/")
    s = re.sub(r"[^\w\-.]", "_", s)
    return s or "default"


def get_cache_folder(endpoint_key_or_path: str) -> Path:
    """
    Retorna a pasta de cache para o endpoint.
    Usa chave curta se for chave conhecida, senão path normalizado.
    """
    path = resolve_path(endpoint_key_or_path)
    if path is not None and "/" not in endpoint_key_or_path:
        # É uma chave; usar a própria chave como nome de pasta
        folder_name = _normalize_for_folder(endpoint_key_or_path)
    else:
        # Path completo: v1/convesation/download-report/agent -> v1_convesation_download-report_agent
        raw = endpoint_key_or_path.lstrip("/") if endpoint_key_or_path else "unknown"
        folder_name = _normalize_for_folder(raw.replace("/", "_"))
    folder = CACHE_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _suffix_from_params(params: dict | None) -> str:
    """Gera sufixo legível a partir dos query params (from, to, agentId). Usado só quando timestamp não é passado."""
    if not params:
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    parts = []
    for k in ("from", "to", "agentId"):
        if k in params and params[k]:
            v = str(params[k])[:50]
            parts.append(f"{k}={v}")
    if not parts:
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return "_".join(parts)


def _cache_suffix(
    endpoint_key_or_path: str,
    params: dict | None,
    timestamp: str | None,
) -> str:
    """
    Sufixo para nomes de arquivo no cache (parte após raw_/optimized_/comparison_).
    Se timestamp for "latest", usa só o slug (ex.: liareport) — nomes curtos, cada chamada substitui.
    Se timestamp for outro valor (ex.: 20260219_143022), usa slug_timestamp.
    Se None, usa sufixo derivado dos params (compatibilidade com cache antigo).
    """
    if timestamp:
        slug = get_endpoint_slug(endpoint_key_or_path) if "/" not in endpoint_key_or_path else "default"
        if timestamp == "latest":
            return slug
        return f"{slug}_{timestamp}"
    return _suffix_from_params(params)


def save_raw(
    endpoint_key_or_path: str,
    data: dict,
    params: dict | None = None,
    timestamp: str | None = None,
) -> Path:
    """
    Salva o JSON bruto na pasta do endpoint.
    Com timestamp="latest" gera raw_<slug>.json (ex.: raw_liareport.json); cada chamada substitui.
    Retorna o Path do arquivo salvo.
    """
    folder = get_cache_folder(endpoint_key_or_path)
    suffix = _cache_suffix(endpoint_key_or_path, params, timestamp)
    safe_suffix = re.sub(r"[^\w\-=.]", "_", suffix)
    fname = f"raw_{safe_suffix}.json"
    path = folder / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_optimized(
    endpoint_key_or_path: str,
    data: dict,
    params: dict | None = None,
    timestamp: str | None = None,
) -> Path:
    """
    Salva o JSON otimizado na pasta do endpoint.
    Com timestamp="latest" gera optimized_<slug>.json (ex.: optimized_liareport.json); cada chamada substitui.
    Retorna o Path do arquivo salvo.
    """
    folder = get_cache_folder(endpoint_key_or_path)
    suffix = _cache_suffix(endpoint_key_or_path, params, timestamp)
    safe_suffix = re.sub(r"[^\w\-=.]", "_", suffix)
    fname = f"optimized_{safe_suffix}.json"
    path = folder / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def save_dashboard(
    endpoint_key_or_path: str,
    data: dict,
    params: dict | None = None,
    timestamp: str | None = None,
) -> Path:
    """
    Salva o JSON tratado para dashboards (visao_geral, etc.) na pasta do endpoint.
    Com timestamp="latest" gera dashboard_<slug>.json (ex.: dashboard_liareport.json); cada chamada substitui.
    Retorna o Path do arquivo salvo. Útil para conferência local da resposta padrão do wrapper.
    """
    folder = get_cache_folder(endpoint_key_or_path)
    suffix = _cache_suffix(endpoint_key_or_path, params, timestamp)
    safe_suffix = re.sub(r"[^\w\-=.]", "_", suffix)
    fname = f"dashboard_{safe_suffix}.json"
    path = folder / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
