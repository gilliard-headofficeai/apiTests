"""
Um comando sobe o servidor wrapper e abre o ngrok em outra janela.
Este terminal fica com os logs do servidor; o ngrok roda na janela do CMD que abrir.
Uso:
  python main.py         # Abre ngrok em nova janela + servidor aqui (logs neste terminal)
  python main.py --no-ngrok   # Só o servidor (sem abrir ngrok)
"""
import argparse
import subprocess
import sys
import time

from src.config import WRAPPER_PORT
from src.wrapper_server import serve


def _open_ngrok_in_new_window():
    """Abre ngrok em uma nova janela (CMD no Windows) para não misturar logs com o servidor."""
    if sys.platform == "win32":
        # start cmd /k = nova janela CMD que mantém aberta com ngrok
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", "ngrok", "http", str(WRAPPER_PORT)])
    else:
        for cmd in [
            ["xterm", "-e", "ngrok", "http", str(WRAPPER_PORT)],
            ["gnome-terminal", "--", "ngrok", "http", str(WRAPPER_PORT)],
        ]:
            try:
                subprocess.Popen(cmd)
                return
            except FileNotFoundError:
                continue
        print("Rode em outro terminal: ngrok http", WRAPPER_PORT, file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wrapper API Report: sobe o servidor e abre ngrok em outra janela (um comando só)"
    )
    parser.add_argument(
        "--no-ngrok",
        action="store_true",
        help="Sobe apenas o servidor, sem abrir a janela do ngrok",
    )
    args = parser.parse_args()

    if not args.no_ngrok:
        try:
            _open_ngrok_in_new_window()
        except Exception as e:
            print("Não foi possível abrir o ngrok em outra janela:", e, file=sys.stderr)
            print("Rode manualmente em outro terminal: ngrok http", WRAPPER_PORT, file=sys.stderr)
        time.sleep(1)
        print()
        print("=" * 60)
        print(f"Wrapper rodando em http://localhost:{WRAPPER_PORT}")
        print("Ngrok aberto em outra janela. Use a URL HTTPS no front.")
        print("Logs das chamadas aparecem abaixo.")
        print("=" * 60)
        print()
    else:
        print()
        print("=" * 60)
        print(f"Wrapper rodando em http://localhost:{WRAPPER_PORT}")
        print("Logs das chamadas aparecem neste terminal.")
        print("=" * 60)
        print()

    serve()
