#!/usr/bin/env python3
"""
Antigravity Bridge Gateway
Servidor ASGI ligero (Starlette + Uvicorn + WebSockets) que enlaza el celular con la PC.
Provee:
- Ejecución remota de comandos en Windows PowerShell desde el celular.
- Chat con Gemini y lectura de repositorios GitHub en la nube (Cloud Inspector).
- Streaming bidireccional por WebSocket.
- Interfaz móvil web (PWA) oscura y responsiva.
"""

import os
import sys
import json
import asyncio
import subprocess
import socket
import pathlib
from typing import Dict, Any, List

# Asegurar que los módulos vecinos estén en el path
BRIDGE_DIR = pathlib.Path(__file__).parent.resolve()
WORKSPACE_DIR = BRIDGE_DIR.parent.resolve()
APP_DIR = WORKSPACE_DIR / "android-app"
sys.path.insert(0, str(WORKSPACE_DIR / "github-cloud"))

import cloud_inspector

from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, Response, FileResponse
from starlette.routing import Route, WebSocketRoute, Mount
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Token de seguridad local (puede ser sobreescrito por variable de entorno)
AUTH_TOKEN = os.environ.get("ANTIGRAVITY_TOKEN", "antigravity-secret-key")

def verify_token(request) -> bool:
    """Valida el token de autenticación desde el header o la query string."""
    token = request.headers.get("X-Antigravity-Token") or request.query_params.get("token")
    return token == AUTH_TOKEN

# ==============================================================================
# Rutas HTTP
# ==============================================================================

async def homepage(request):
    """Sirve la aplicación Android Antigravity Mobile Hub."""
    html_path = APP_DIR / "index.html"
    if not html_path.exists():
        html_path = BRIDGE_DIR / "static" / "index.html"
    content = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content)

async def serve_manifest(request):
    manifest_path = APP_DIR / "manifest.json"
    return FileResponse(manifest_path, media_type="application/manifest+json")

async def serve_sw(request):
    sw_path = APP_DIR / "service-worker.js"
    return FileResponse(sw_path, media_type="application/javascript")

async def api_status(request):
    """Devuelve estado y telemetría de la PC anfitriona."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    hostname = socket.gethostname()
    os_name = sys.platform
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    has_github = bool(cloud_inspector.get_github_token())

    return JSONResponse({
        "status": "online",
        "hostname": hostname,
        "os": os_name,
        "workspace": str(WORKSPACE_DIR),
        "gemini_configured": has_gemini,
        "github_authenticated": has_github,
    })

async def api_repos(request):
    """Devuelve los repositorios de GitHub en la nube del usuario."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    owner = request.query_params.get("owner", "zero-phoenix")
    res = cloud_inspector.cloud_list_repositories(owner)
    return JSONResponse(res)

async def api_tree(request):
    """Devuelve el árbol de archivos en la nube de un repositorio."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    repo = request.query_params.get("repo")
    if not repo:
        return JSONResponse({"error": "Parámetro 'repo' requerido"}, status_code=400)

    branch = request.query_params.get("branch")
    res = cloud_inspector.cloud_get_tree(repo, branch=branch)
    return JSONResponse(res)

async def api_file(request):
    """Devuelve el contenido en memoria de un archivo en la nube."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    repo = request.query_params.get("repo")
    path = request.query_params.get("path")
    if not repo or not path:
        return JSONResponse({"error": "Parámetros 'repo' y 'path' requeridos"}, status_code=400)

    start_line = int(request.query_params.get("start", 1))
    end_line = int(request.query_params.get("end", 300))
    res = cloud_inspector.cloud_read_file(repo, path, start_line=start_line, end_line=end_line)
    return JSONResponse(res)

async def api_exec(request):
    """Ejecuta un comando de PowerShell en la PC y devuelve stdout/stderr."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    try:
        body = await request.json()
        cmd = body.get("command", "").strip()
    except Exception:
        cmd = ""

    if not cmd:
        return JSONResponse({"error": "Comando vacío"}, status_code=400)

    # Ejecutar en PowerShell de Windows
    proc = await asyncio.create_subprocess_shell(
        f"powershell -Command {json.dumps(cmd)}",
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    return JSONResponse({
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
    })

# ==============================================================================
# WebSocket Bidireccional
# ==============================================================================

async def websocket_endpoint(websocket: WebSocket):
    """
    Canal WebSocket para streaming en tiempo real entre el celular y la PC.
    Soporta:
    - Comandos de terminal en vivo.
    - Chat interactivo con Gemini conectado a Cloud Inspector y herramientas del sistema.
    """
    await websocket.accept()
    token = websocket.query_params.get("token")
    if token != AUTH_TOKEN:
        await websocket.send_json({"event": "error", "message": "Token de autenticación inválido"})
        await websocket.close()
        return

    await websocket.send_json({"event": "connected", "message": "Enlace Antigravity establecido con éxito"})

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            if msg_type == "exec":
                # Ejecutar comando en PowerShell con streaming
                cmd = data.get("command", "").strip()
                if not cmd:
                    continue

                await websocket.send_json({"event": "exec_start", "command": cmd})
                proc = await asyncio.create_subprocess_shell(
                    f"powershell -Command {json.dumps(cmd)}",
                    cwd=str(WORKSPACE_DIR),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                # Leer stdout línea por línea y transmitir al celular
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    await websocket.send_json({
                        "event": "stdout_chunk",
                        "text": line.decode("utf-8", errors="replace")
                    })

                stderr = await proc.stderr.read()
                await proc.wait()

                await websocket.send_json({
                    "event": "exec_end",
                    "exit_code": proc.returncode,
                    "stderr": stderr.decode("utf-8", errors="replace") if stderr else ""
                })

            elif msg_type == "chat":
                prompt = data.get("prompt", "").strip()
                options = data.get("options", {})
                target_model = options.get("model", "gemini-2.5-flash")
                temp = float(options.get("temperature", 0.2))
                strict = options.get("strict", True)
                if not prompt:
                    continue

                await websocket.send_json({"event": "chat_thinking", "prompt": prompt})

                # Si no hay GEMINI_API_KEY, avisar
                if not os.environ.get("GEMINI_API_KEY"):
                    await websocket.send_json({
                        "event": "chat_error",
                        "message": "GEMINI_API_KEY no configurada en la PC. Ejecuta .\\gemini\\setup_key.ps1."
                    })
                    continue

                # Ejecutar consulta con Gemini y Cloud Tools
                try:
                    from google import genai
                    from google.genai import types

                    def delegate_to_desktop(command: str) -> Dict[str, Any]:
                        """
                        Ejecuta un comando de PowerShell en la PC anfitriona Windows (compilar, editar archivos, git, tests)
                        y devuelve la salida para que Gemini la analice.
                        """
                        try:
                            proc = subprocess.run(
                                ["powershell", "-Command", command],
                                cwd=str(WORKSPACE_DIR),
                                capture_output=True,
                                text=True,
                                timeout=120
                            )
                            return {
                                "command": command,
                                "exit_code": proc.returncode,
                                "stdout": proc.stdout[-4000:] if len(proc.stdout) > 4000 else proc.stdout,
                                "stderr": proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
                            }
                        except Exception as e:
                            return {"error": f"Error ejecutando en PC: {str(e)}"}

                    client = genai.Client()
                    tools = [
                        cloud_inspector.cloud_list_repositories,
                        cloud_inspector.cloud_get_tree,
                        cloud_inspector.cloud_read_file,
                        cloud_inspector.cloud_search_code,
                        cloud_inspector.cloud_compare_files,
                        delegate_to_desktop,
                    ]

                    # Mapeo de ejecución local
                    active_tools_map = dict(cloud_inspector.CLOUD_TOOLS_MAP)
                    active_tools_map["delegate_to_desktop"] = delegate_to_desktop

                    system_instruction = (
                        "Eres Antigravity Mobile Hub. El usuario te habla desde su celular conectado a su cuenta de GitHub (zero-phoenix) y su PC. "
                        "Tienes acceso a inspeccionar repositorios en la nube (cloud_*) propios y de terceros, y puedes DELEGAR comandos "
                        "a la PC de Windows mediante 'delegate_to_desktop' para ejecutar git, compilaciones, tests o inspecciones locales. "
                    )
                    if strict:
                        system_instruction += (
                            "POLÍTICA ESTRICTA DE GROUNDING: Tienes terminantemente prohibido inventar código o asumir APIs inexistentes. "
                            "Básate EXCLUSIVAMENTE en lo verificado a través de las herramientas de inspección o comandos de la PC. "
                            "Cita siempre archivo y línea de referencia."
                        )

                    chat = client.chats.create(
                        model=target_model,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temp,
                            tools=tools,
                        )
                    )

                    response = chat.send_message(prompt)
                    turn = 0
                    while turn < 10 and response.function_calls:
                        turn += 1
                        tool_responses = []
                        for call in response.function_calls:
                            fn_name = call.name
                            fn_args = dict(call.args) if call.args else {}
                            await websocket.send_json({
                                "event": "chat_tool_call",
                                "tool": fn_name,
                                "args": fn_args
                            })

                            if fn_name in active_tools_map:
                                res = active_tools_map[fn_name](**fn_args)
                            else:
                                res = {"error": f"Herramienta desconocida: {fn_name}"}

                            tool_responses.append(
                                types.Part.from_function_response(
                                    name=fn_name,
                                    response={"result": res}
                                )
                            )

                        response = chat.send_message(tool_responses)

                    await websocket.send_json({
                        "event": "chat_response",
                        "text": response.text or ""
                    })

                except Exception as ex:
                    await websocket.send_json({"event": "chat_error", "message": str(ex)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except Exception:
            pass

# ==============================================================================
# Definición de la Aplicación Starlette
# ==============================================================================

routes = [
    Route("/", homepage),
    Route("/manifest.json", serve_manifest),
    Route("/service-worker.js", serve_sw),
    Route("/api/status", api_status),
    Route("/api/repos", api_repos),
    Route("/api/tree", api_tree),
    Route("/api/file", api_file),
    Route("/api/exec", api_exec, methods=["POST"]),
    WebSocketRoute("/ws/stream", websocket_endpoint),
    Mount("/css", StaticFiles(directory=str(APP_DIR / "css")), name="css"),
    Mount("/js", StaticFiles(directory=str(APP_DIR / "js")), name="js"),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8765))
    print(f"Iniciando Antigravity Bridge en http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
