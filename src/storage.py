"""
Persistência local: cria pasta por endpoint (chave ou path normalizado) e salva JSON bruto/otimizado.
Nomes de arquivo no cache seguem o padrão: raw_<slug>_<timestamp>.json e optimized_<slug>_<timestamp>.json
(ex.: raw_liareport_20260219_143022.json), para reutilização em outras soluções.
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
    Sufixo para nomes de arquivo no cache.
    Se timestamp for "latest", usa slug_latest (ex.: liareport_latest) e cada nova chamada substitui o arquivo.
    Se timestamp for outro valor, usa slug_timestamp. Se None, usa sufixo derivado dos params.
    """
    if timestamp:
        slug = get_endpoint_slug(endpoint_key_or_path) if "/" not in endpoint_key_or_path else "default"
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
    Se timestamp for passado (ex.: 20260219_143022), o arquivo será raw_<slug>_<timestamp>.json.
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
    Use o mesmo timestamp passado a save_raw na mesma requisição para manter par raw/optimized.
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
