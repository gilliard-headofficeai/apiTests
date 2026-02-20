"""
Configuração do wrapper: BASE_URL da API real, pasta de cache, porta do servidor
e carga do arquivo de endereçamento (chave -> path real).
Responsabilidade: centralizar variáveis de ambiente e mapeamento de endpoints (path, default_params, slug para nomes de cache).
"""
import os
from pathlib import Path
import json

# Carregar .env: raiz do projeto (onde está src/) e depois cwd (override)
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
    _cwd_env = Path.cwd() / ".env"
    if _cwd_env.exists():
        load_dotenv(_cwd_env, override=True)
except ImportError:
    pass

# Raiz do projeto (pasta que contém src/ e config/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Variáveis de ambiente (com fallback)
# URL da API real. No Windows, 0.0.0.0 não funciona como cliente → sempre usar localhost
_raw_base = os.getenv("WRAPPER_BASE_URL", "http://localhost:3000").strip().rstrip("/")
if "0.0.0.0" in _raw_base:
    _raw_base = _raw_base.replace("0.0.0.0", "localhost")
# Se ainda veio 0.0.0.0 (ex.: .env pai), tentar ler do .env do projeto
if "0.0.0.0" in _raw_base and (PROJECT_ROOT / ".env").exists():
    try:
        for line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("WRAPPER_BASE_URL=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'").rstrip("/")
                if val and "localhost" in val:
                    _raw_base = val.replace("0.0.0.0", "localhost")
                    break
    except Exception:
        pass
BASE_URL = _raw_base.replace("0.0.0.0", "localhost")
CACHE_DIR = Path(os.getenv("WRAPPER_CACHE_DIR", str(PROJECT_ROOT / "cache")))
WRAPPER_PORT = int(os.getenv("WRAPPER_PORT", "8000"))
# Chave da API real de relatório (enviada no header das chamadas)
GENERAL_REPORT_API_KEY = os.getenv("GENERAL_REPORT_API_KEY", "").strip()
if not GENERAL_REPORT_API_KEY and (PROJECT_ROOT / ".env").exists():
    try:
        for line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GENERAL_REPORT_API_KEY=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    GENERAL_REPORT_API_KEY = val
                    break
    except Exception:
        pass

# Caminho do arquivo de endereçamento
ENDPOINTS_FILE = PROJECT_ROOT / "config" / "api_endpoints.json"

# Cache do mapeamento (carregado sob demanda)
_endpoints_map: dict | None = None
_endpoints_full: dict | None = None

# Slug curto por endpoint para nomes de arquivo no cache (ex.: report_lia -> liareport)
# Padrão de nomes no cache: raw_liareport.json, optimized_liareport.json (slug curto por endpoint)
ENDPOINT_SLUGS: dict[str, str] = {"report_lia": "liareport"}


def get_endpoint_slug(endpoint_key: str) -> str:
    """
    Retorna um slug curto para o endpoint, usado em nomes de arquivo no cache.
    Ex.: report_lia -> liareport. Endpoints não mapeados usam a chave normalizada (underscores).
    """
    if endpoint_key in ENDPOINT_SLUGS:
        return ENDPOINT_SLUGS[endpoint_key]
    return endpoint_key.replace("-", "_").strip() or "default"


def _load_endpoints_raw() -> dict:
    """Carrega o JSON bruto de api_endpoints.json (chave -> path string ou dict com path + default_params)."""
    global _endpoints_full
    if _endpoints_full is not None:
        return _endpoints_full
    if not ENDPOINTS_FILE.exists():
        _endpoints_full = {}
        return _endpoints_full
    with open(ENDPOINTS_FILE, encoding="utf-8") as f:
        _endpoints_full = json.load(f)
    return _endpoints_full


def load_endpoints() -> dict[str, str]:
    """Carrega o mapeamento chave -> path real (apenas paths) para compatibilidade."""
    global _endpoints_map
    if _endpoints_map is not None:
        return _endpoints_map
    raw = _load_endpoints_raw()
    _endpoints_map = {}
    for key, value in raw.items():
        if isinstance(value, str):
            _endpoints_map[key] = value
        elif isinstance(value, dict) and "path" in value:
            _endpoints_map[key] = value["path"]
    return _endpoints_map


def get_endpoint_config(endpoint_key: str) -> dict | None:
    """
    Retorna a configuração completa do endpoint: path e default_params.
    default_params são os parâmetros fixos (ex.: agentId, by, messageHistory) que o backend
    adiciona à chamada real sem o frontend precisar enviar.
    """
    if "/" in endpoint_key:
        return {"path": endpoint_key.lstrip("/"), "default_params": {}}
    raw = _load_endpoints_raw()
    val = raw.get(endpoint_key)
    if val is None:
        return None
    if isinstance(val, str):
        return {"path": val, "default_params": {}}
    if isinstance(val, dict) and "path" in val:
        default = val.get("default_params")
        if not isinstance(default, dict):
            default = {}
        # Resolver placeholders ${VAR} com variáveis de ambiente (ex.: agentId no .env)
        resolved = {}
        for k, v in default.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1].strip()
                resolved[k] = os.getenv(env_key, "")
            else:
                resolved[k] = v
        return {"path": val["path"], "default_params": resolved}
    return None


def resolve_path(endpoint_key_or_path: str) -> str | None:
    """
    Resolve um identificador para o path real da API.
    Se for chave do api_endpoints.json, retorna o path; se já for um path (contém '/'), retorna normalizado.
    Retorna None se for chave inexistente.
    """
    cfg = get_endpoint_config(endpoint_key_or_path)
    return cfg["path"] if cfg else None
