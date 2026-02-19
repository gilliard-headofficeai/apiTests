"""
Sobe o servidor wrapper e inicia ngrok (ngrok http 8000) para teste (ex.: Lovable).
Uso: python main.py
- Servidor local: http://localhost:8000
- Ngrok roda em subprocess; use a URL que aparecer no terminal do ngrok no Lovable.
Responsabilidade: ponto de entrada para desenvolvimento; inicia wrapper em thread e expõe com ngrok.
"""
import subprocess
import sys
import time
import threading

from src.config import WRAPPER_PORT
from src.wrapper_server import serve


def _run_server():
    """Roda uvicorn em thread para não bloquear o main."""
    serve()


if __name__ == "__main__":
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    print()
    print("=" * 60)
    print(f"Wrapper rodando em http://localhost:{WRAPPER_PORT}")
    print("Iniciando ngrok http 8000...")
    print("Use a URL HTTPS que o ngrok mostrar no Lovable, ex.:")
    print("  https://xxxx.ngrok-free.app/wrapper/report_lia?from=2026-01-01&to=2026-01-14")
    print("=" * 60)
    print()

    try:
        subprocess.run(["ngrok", "http", str(WRAPPER_PORT)])
    except FileNotFoundError:
        print("Ngrok não encontrado no PATH. Rode em outro terminal: ngrok http 8000", file=sys.stderr)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nEncerrando.")
        sys.exit(0)
