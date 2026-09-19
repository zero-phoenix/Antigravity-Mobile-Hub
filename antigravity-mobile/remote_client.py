#!/usr/bin/env python3
"""
Cliente Remoto Antigravity Mobile para Termux / Android CLI.
Permite enviar comandos de terminal o prompts de Gemini desde la consola del celular
hacia la PC que ejecuta Antigravity Bridge.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def send_exec(server: str, token: str, command: str):
    url = f"http://{server}/api/exec"
    headers = {
        "Content-Type": "application/json",
        "X-Antigravity-Token": token
    }
    data = json.dumps({"command": command}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    print(f"\n[*] Enviando comando a la PC ({server}): {command}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"\n[PC Output] Exit Code: {res.get('exit_code')}")
            if res.get("stdout"):
                print(res["stdout"])
            if res.get("stderr"):
                print(f"[STDERR]\n{res['stderr']}")
    except Exception as e:
        print(f"[ERROR] No se pudo comunicar con el servidor: {e}")

def check_status(server: str, token: str):
    url = f"http://{server}/api/status?token={urllib.parse.quote(token)}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\n[OK] Estado del Servidor PC:")
            print(f"    Host        : {data.get('hostname')} ({data.get('os')})")
            print(f"    Workspace   : {data.get('workspace')}")
            print(f"    Gemini      : {'Configurado' if data.get('gemini_configured') else 'Sin API Key'}")
            print(f"    GitHub      : {'Autenticado' if data.get('github_authenticated') else 'No autenticado'}")
    except Exception as e:
        print(f"[ERROR] Servidor no responde en {server}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Mobile Remote Client")
    parser.add_argument("--server", default="127.0.0.1:8765", help="Dirección IP y puerto de la PC (ej. 192.168.1.50:8765)")
    parser.add_argument("--token", default="antigravity-secret-key", help="Token de seguridad")
    parser.add_argument("--status", action="store_true", help="Verifica el estado de la PC")
    parser.add_argument("command", nargs="*", help="Comando de PowerShell para ejecutar en la PC")
    args = parser.parse_args()

    if args.status or not args.command:
        check_status(args.server, args.token)
        if not args.command:
            return

    cmd_str = " ".join(args.command)
    send_exec(args.server, args.token, cmd_str)

if __name__ == "__main__":
    main()
