"""
Orquestra: chama API real, salva bruto, otimiza e retorna JSON.
Modos: CLI (script com argumentos) e servidor HTTP (FastAPI).
"""
import argparse
import json
import sys
from pathlib import Path

# Garantir que o projeto root esteja no path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api_client import fetch_json
from src.storage import save_raw, save_optimized
from src.optimizer import optimize_report_response


def run_once(
    endpoint_key_or_path: str,
    params: dict | None = None,
    save_optimized_file: bool = True,
) -> dict:
    """
    Executa um ciclo: fetch -> salvar bruto -> otimizar -> salvar otimizado (opcional).
    Retorna o JSON otimizado.
    """
    raw = fetch_json(endpoint_key_or_path, params=params)
    save_raw(endpoint_key_or_path, raw, params=params)
    optimized = optimize_report_response(raw)
    if save_optimized_file:
        save_optimized(endpoint_key_or_path, optimized, params=params)
    return optimized


def cli():
    """Interface de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Wrapper da API de report: chama a API real, salva o bruto e devolve JSON otimizado."
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Chave do api_endpoints.json (ex: report_agent) ou path (ex: v1/convesation/download-report/agent)",
    )
    parser.add_argument("--by", default=None, help="Query param: by")
    parser.add_argument("--messageHistory", default=None, help="Query param: messageHistory")
    parser.add_argument("--agentId", default=None, help="Query param: agentId")
    parser.add_argument("--from", dest="from_", default=None, help="Query param: from (data início)")
    parser.add_argument("--to", default=None, help="Query param: to (data fim)")
    parser.add_argument(
        "--no-save-optimized",
        action="store_true",
        help="Não salvar arquivo optimized_*.json no cache",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Salvar JSON otimizado neste arquivo (em vez de imprimir)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Subir servidor HTTP em vez de executar uma chamada",
    )
    args = parser.parse_args()

    if args.serve:
        from src.wrapper_server import serve
        serve()
        return

    params = {}
    if args.by is not None:
        params["by"] = args.by
    if args.messageHistory is not None:
        params["messageHistory"] = args.messageHistory
    if args.agentId is not None:
        params["agentId"] = args.agentId
    if args.from_ is not None:
        params["from"] = args.from_
    if args.to is not None:
        params["to"] = args.to

    optimized = run_once(
        args.endpoint,
        params=params if params else None,
        save_optimized_file=not args.no_save_optimized,
    )
    text = json.dumps(optimized, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    cli()
