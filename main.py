"""
Sobe o servidor wrapper e expõe via ngrok para teste (ex.: Lovable).
Uso: python main.py
- Servidor local: http://localhost:8000
- URL pública ngrok impressa no console (use no Lovable para testar).
"""
import sys
import time
import threading

from src.config import WRAPPER_PORT
from src.wrapper_server import serve


def _run_server():
    """Roda uvicorn em thread para não bloquear o main."""
    serve()


if __name__ == "__main__":
    # Servidor em thread para podermos iniciar o ngrok em seguida
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    ngrok_url = None
    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(WRAPPER_PORT)
        ngrok_url = tunnel.public_url
        print()
        print("=" * 60)
        print("Wrapper rodando.")
        print(f"  Local:  http://localhost:{WRAPPER_PORT}")
        print(f"  Ngrok:  {ngrok_url}")
        print()
        print("No Lovable, use a URL do ngrok + rota, ex.:")
        print(f"  {ngrok_url}/wrapper/report_lia?from=2026-01-01&to=2026-01-14")
        print("=" * 60)
        print()
    except Exception as e:
        print(f"Ngrok não iniciado: {e}", file=sys.stderr)
        print(f"Servidor local: http://localhost:{WRAPPER_PORT}", file=sys.stderr)
        print("Para expor na internet, rode em outro terminal: ngrok http 8000", file=sys.stderr)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nEncerrando.")
        sys.exit(0)
