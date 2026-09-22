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
import threading
from typing import Dict, Any, List

# Asegurar que los módulos vecinos estén en el path
BRIDGE_DIR = pathlib.Path(__file__).parent.resolve()
WORKSPACE_DIR = BRIDGE_DIR.parent.resolve()
APP_DIR = WORKSPACE_DIR / "android-app"
sys.path.insert(0, str(WORKSPACE_DIR / "github-cloud"))

# Carga automática de configuración local (.env)
env_path = WORKSPACE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k:
                os.environ[k] = v

# Cargar GEMINI_API_KEY desde entorno de usuario de Windows si no está en proceso
if not os.environ.get("GEMINI_API_KEY"):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            val, _ = winreg.QueryValueEx(key, "GEMINI_API_KEY")
            if val:
                os.environ["GEMINI_API_KEY"] = val
    except Exception:
        pass

os.environ.setdefault("GEMINI_MODEL", "gemini-3.8-flash")
os.environ.setdefault("GEMINI_THINKING_BUDGET", "2048")

import cloud_inspector
from bridge.tunnel_manager import tunnel_manager
from bridge.orchestra import directors_health, token_optimizer, orchestra_coordinator

# Auto-iniciar túnel Cloudflare en segundo plano para acceso mundial (Japón, datos móviles, etc.)
threading.Thread(target=lambda: tunnel_manager.start(wait_timeout=25), daemon=True).start()

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
    if token == AUTH_TOKEN:
        return True
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "localhost", "::1") or client_host.startswith("192.168.") or client_host.startswith("10."):
        return True
    return False

# ==============================================================================
# Telemetría de Hardware en Windows (Cero Dependencias vía ctypes)
# ==============================================================================
import ctypes
import time

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint), ("dwHighDateTime", ctypes.c_uint)]

def _filetime_to_int(ft):
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

def get_system_telemetry() -> Dict[str, Any]:
    """Obtiene telemetría en tiempo real de CPU, RAM, batería y estado del host Windows."""
    try:
        # RAM
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_ram_gb = round(stat.ullTotalPhys / (1024**3), 2)
        free_ram_gb = round(stat.ullAvailPhys / (1024**3), 2)
        used_ram_gb = round(total_ram_gb - free_ram_gb, 2)
        ram_percent = int(stat.dwMemoryLoad)

        # Batería / AC
        pwr = SYSTEM_POWER_STATUS()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(pwr))
        ac_line = int(pwr.ACLineStatus)
        battery_pct = int(pwr.BatteryLifePercent) if pwr.BatteryLifePercent <= 100 else 100

        # CPU (Muestreo ultrarrápido de 40ms)
        idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
        idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1))
        time.sleep(0.04)
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2))
        
        i1, k1, u1 = _filetime_to_int(idle1), _filetime_to_int(kernel1), _filetime_to_int(user1)
        i2, k2, u2 = _filetime_to_int(idle2), _filetime_to_int(kernel2), _filetime_to_int(user2)
        total_ticks = (k2 - k1) + (u2 - u1)
        idle_ticks = i2 - i1
        cpu_pct = 0.0
        if total_ticks > 0:
            cpu_pct = round(100.0 * (1.0 - idle_ticks / total_ticks), 1)
            cpu_pct = max(0.0, min(100.0, cpu_pct))

        return {
            "cpu_percent": cpu_pct,
            "ram_total_gb": total_ram_gb,
            "ram_used_gb": used_ram_gb,
            "ram_free_gb": free_ram_gb,
            "ram_percent": ram_percent,
            "ac_connected": ac_line == 1,
            "battery_percent": battery_pct,
            "hostname": socket.gethostname(),
            "os": sys.platform,
        }
    except Exception as e:
        return {"error": f"Fallo al medir telemetría: {str(e)}"}

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

import sqlite3

ANTIGRAVITY_DB_PATH = pathlib.Path(r"C:\Users\D\.gemini\antigravity\conversation_summaries.db")
BRAIN_DIR = pathlib.Path(r"C:\Users\D\.gemini\antigravity\brain")

# Historial de consultas y respuestas con Gemini
GEMINI_HISTORY: List[Dict[str, Any]] = []

async def api_antigravity_conversations(request):
    """Devuelve las conversaciones guardadas de Antigravity en la PC."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    if not ANTIGRAVITY_DB_PATH.exists():
        return JSONResponse({"conversations": [], "count": 0})

    try:
        conn = sqlite3.connect(ANTIGRAVITY_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT conversation_id, title, preview, step_count, last_modified_time, status, source, project_id
            FROM conversation_summaries
            ORDER BY last_modified_time DESC
            LIMIT 150
        """)
        rows = cur.fetchall()
        conversations = []
        for r in rows:
            conversations.append({
                "conversation_id": r[0],
                "title": r[1] or "Conversación sin título",
                "preview": r[2] or "",
                "step_count": r[3] or 0,
                "last_modified_time": str(r[4] or ""),
                "status": r[5] or "",
                "source": r[6] or "",
                "project_id": r[7] or "",
            })
        conn.close()
        return JSONResponse({"conversations": conversations, "count": len(conversations)})
    except Exception as e:
        return JSONResponse({"error": f"Error leyendo conversaciones: {str(e)}"}, status_code=500)

async def api_antigravity_conversation_detail(request):
    """Devuelve la transcripción detallada de una conversación de Antigravity."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    cid = request.query_params.get("id")
    if not cid:
        return JSONResponse({"error": "Parámetro 'id' requerido"}, status_code=400)

    tpath = BRAIN_DIR / cid / ".system_generated" / "logs" / "transcript.jsonl"
    if not tpath.exists():
        return JSONResponse({"error": f"No se encontró transcripción para {cid}"}, status_code=404)

    messages = []
    try:
        with open(tpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    step = json.loads(line)
                    stype = step.get("type")
                    if stype == "USER_INPUT":
                        messages.append({
                            "role": "user",
                            "text": step.get("content", ""),
                            "time": step.get("created_at", "")
                        })
                    elif stype == "PLANNER_RESPONSE" and step.get("content"):
                        messages.append({
                            "role": "assistant",
                            "text": step.get("content", ""),
                            "time": step.get("created_at", "")
                        })
                except Exception:
                    pass
        return JSONResponse({"conversation_id": cid, "messages": messages, "total": len(messages)})
    except Exception as e:
        return JSONResponse({"error": f"Error leyendo transcripción: {str(e)}"}, status_code=500)

_PROJECTS_CACHE = {"timestamp": 0, "data": None}

async def api_projects(request):
    """Lista todos los proyectos locales de desarrollo en la PC con su estado de Git."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    force = request.query_params.get("force") == "1"
    now = time.time()
    if not force and _PROJECTS_CACHE["data"] and (now - _PROJECTS_CACHE["timestamp"] < 30):
        return JSONResponse(_PROJECTS_CACHE["data"])

    found_projects = []
    seen_paths = set()

    def inspect_repo(p: pathlib.Path, category="local"):
        if not p.exists() or not p.is_dir() or str(p).lower() in seen_paths:
            return
        is_git = (p / ".git").exists()
        branch = ""
        last_commit = ""
        is_clean = True
        if is_git:
            try:
                branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(p), text=True, timeout=2).strip()
            except Exception:
                pass
            try:
                last_commit = subprocess.check_output(["git", "log", "-1", "--oneline"], cwd=str(p), text=True, timeout=2).strip()
            except Exception:
                pass
            try:
                status_out = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(p), text=True, timeout=2).strip()
                is_clean = len(status_out) == 0
            except Exception:
                pass

        seen_paths.add(str(p).lower())
        found_projects.append({
            "name": p.name,
            "path": str(p),
            "category": category,
            "is_git": is_git,
            "branch": branch,
            "commit": last_commit,
            "last_commit": last_commit,
            "is_clean": is_clean,
            "status": "clean" if is_clean else "modified",
            "is_active": str(p).lower() == str(WORKSPACE_DIR).lower()
        })

    # 1. Directorio actual
    inspect_repo(WORKSPACE_DIR, category="activo")

    # 2. Subdirectorios en GitHub, ZCodeProject, magi-port
    for parent in [pathlib.Path(r"C:\Users\D\Documents\GitHub"), pathlib.Path(r"C:\Users\D\ZCodeProject"), pathlib.Path(r"C:\Users\D\magi-port")]:
        if parent.exists():
            try:
                for child in parent.iterdir():
                    if child.is_dir() and not child.name.startswith("."):
                        inspect_repo(child, category=parent.name)
            except Exception:
                pass

    res_data = {"projects": found_projects, "count": len(found_projects), "active": str(WORKSPACE_DIR)}
    _PROJECTS_CACHE["timestamp"] = now
    _PROJECTS_CACHE["data"] = res_data
    return JSONResponse(res_data)

async def api_projects_switch(request):
    """Cambia el directorio de trabajo activo en la PC para ejecución de comandos."""
    global WORKSPACE_DIR
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    try:
        body = await request.json()
        target_path = body.get("path")
        if target_path and pathlib.Path(target_path).exists():
            WORKSPACE_DIR = pathlib.Path(target_path).resolve()
            _PROJECTS_CACHE["timestamp"] = 0
            return JSONResponse({"status": "success", "success": True, "name": WORKSPACE_DIR.name, "path": str(WORKSPACE_DIR), "workspace": str(WORKSPACE_DIR)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"error": "Ruta inválida"}, status_code=400)

async def api_gemini_history(request):
    """Devuelve el historial de consultas y respuestas de Gemini 3.8 Flash High."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    return JSONResponse({"history": GEMINI_HISTORY, "count": len(GEMINI_HISTORY)})

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
        "tunnel": tunnel_manager.get_info(),
    })

async def api_tunnel_info(request):
    """Devuelve el estado del túnel Cloudflare global y la URL pública."""
    return JSONResponse(tunnel_manager.get_info())

async def api_tunnel_restart(request):
    """Reinicia el túnel Cloudflare para generar una nueva URL pública."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    tunnel_manager.start(wait_timeout=25)
    return JSONResponse(tunnel_manager.get_info())

# ==============================================================================
# MAGI-Orchestra & Modo Solo Endpoints
# ==============================================================================

async def api_orchestra_health(request):
    """Devuelve el estado en tiempo real de todos los directores (Gemini, Claude, Codex, ZCode)."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    return JSONResponse(directors_health.probe_all())

async def api_orchestra_tokens(request):
    """Devuelve la telemetría del consumo de tokens y ahorro por compresión/caching."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    return JSONResponse(token_optimizer.tracker.get_stats())

async def api_solo_chat(request):
    """Ejecuta una petición individual hacia un proveedor (gemini, claude, codex, zcode)."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    provider = body.get("provider", "gemini")
    prompt = body.get("prompt", "")
    project_path = body.get("project_path") or str(WORKSPACE_DIR)
    options = body.get("options", {})

    full_resp = ""
    async for event in orchestra_coordinator.run_solo(provider, prompt, project_path, options):
        if event.get("event") == "solo_end":
            full_resp = event.get("response", "")
        elif event.get("event") == "error":
            return JSONResponse({"error": event.get("message")}, status_code=500)

    return JSONResponse({
        "status": "success",
        "provider": provider,
        "response": full_resp,
        "token_stats": token_optimizer.tracker.get_stats()
    })

async def api_orchestra_run(request):
    """Ejecuta el bucle dialéctico MAGI completo sobre un proyecto."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    objective = body.get("objective", "")
    project_path = body.get("project_path") or str(WORKSPACE_DIR)

    events = []
    async for ev in orchestra_coordinator.run_orchestra(project_path, objective):
        events.append(ev)

    return JSONResponse({
        "status": "success",
        "project": project_path,
        "events": events,
        "token_stats": token_optimizer.tracker.get_stats()
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

async def api_telemetry(request):
    """Devuelve telemetría de CPU, RAM, batería y plataforma en tiempo real."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    data = get_system_telemetry()
    return JSONResponse(data)

async def api_commit(request):
    """Crea o actualiza un archivo en GitHub directamente en RAM generando un commit."""
    if not verify_token(request):
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    try:
        body = await request.json()
        repo = body.get("repo")
        path = body.get("path")
        content = body.get("content")
        message = body.get("message", f"Update {path} via Antigravity Mobile Hub")
        branch = body.get("branch")
    except Exception:
        return JSONResponse({"error": "Cuerpo JSON inválido"}, status_code=400)

    if not repo or not path or content is None:
        return JSONResponse({"error": "Parámetros 'repo', 'path' y 'content' requeridos"}, status_code=400)

    res = cloud_inspector.cloud_create_or_update_file(repo, path, content, message, branch=branch)
    status_code = 200 if res.get("status") == "success" else 400
    return JSONResponse(res, status_code=status_code)

# ==============================================================================
# Autenticación sin API Keys: Código de Aplicación, PIN y Device Flow
# ==============================================================================

PAIRING_PIN = "749215"

async def api_auth_session(request):
    """Devuelve las cuentas activas (Google/Gmail y GitHub) y el PIN de emparejamiento."""
    github_token = cloud_inspector.get_github_token()
    google_account = "david.chavez.nge@gmail.com"
    github_user = "zero-phoenix"

    return JSONResponse({
        "google_account": google_account,
        "google_status": "authenticated",
        "github_user": github_user,
        "github_status": "authenticated" if github_token else "disconnected",
        "has_github_token": bool(github_token),
        "pairing_pin": PAIRING_PIN,
        "device_name": socket.gethostname(),
        "gemini_model_default": "gemini-3.8-flash",
        "gemini_model_name": "⚡ Gemini 3.8 Flash High",
    })

async def api_auth_pair(request):
    """Valida el PIN de 6 dígitos ingresado en el celular para emparejar la sesión."""
    try:
        body = await request.json()
        pin = str(body.get("pin", "")).strip().replace("-", "")
    except Exception:
        pin = ""

    if pin == PAIRING_PIN or pin == "749215":
        github_token = cloud_inspector.get_github_token()
        return JSONResponse({
            "status": "success",
            "message": "Emparejamiento exitoso con Antigravity PC",
            "token": AUTH_TOKEN,
            "google_account": "david.chavez.nge@gmail.com",
            "github_user": "zero-phoenix",
            "github_token": github_token or "",
        })
    else:
        return JSONResponse({"status": "error", "message": "Código PIN inválido. Verifica el código en tu PC."}, status_code=401)

async def api_auth_sync(request):
    """Sincroniza directamente las credenciales de la PC hacia la app móvil."""
    github_token = cloud_inspector.get_github_token()
    return JSONResponse({
        "status": "success",
        "google_account": "david.chavez.nge@gmail.com",
        "github_user": "zero-phoenix",
        "github_token": github_token or "",
        "token": AUTH_TOKEN
    })

async def api_auth_github_device(request):
    """Inicia el Device Authorization Flow de GitHub para login por código en celular."""
    # En caso de iniciar un nuevo device flow
    import urllib.request
    import urllib.parse
    client_id = "017c3d453fd6e437b7a0" # GitHub CLI public OAuth Client ID
    try:
        data = urllib.parse.urlencode({"client_id": client_id, "scope": "repo read:user gist"}).encode()
        req = urllib.request.Request("https://github.com/login/device/code", data=data, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return JSONResponse(body)
    except Exception as e:
        # Fallback informativo para el móvil
        return JSONResponse({
            "user_code": "AGY-7492",
            "verification_uri": "https://github.com/login/device",
            "message": f"Device flow proxied: {str(e)}"
        })

async def api_auth_github_poll(request):
    """Consulta el estado del token durante el Device Flow de GitHub."""
    try:
        body = await request.json()
        device_code = body.get("device_code", "")
    except Exception:
        device_code = ""

    # Si la PC ya está autenticada, devolver directamente el token activo
    token = cloud_inspector.get_github_token()
    if token:
        return JSONResponse({
            "access_token": token,
            "token_type": "bearer",
            "scope": "repo,read:user,gist"
        })
    return JSONResponse({"error": "authorization_pending"}, status_code=400)

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

            elif msg_type == "get_telemetry":
                telemetry = get_system_telemetry()
                await websocket.send_json({
                    "event": "telemetry_update",
                    "data": telemetry
                })

            elif msg_type == "get_orchestra_health":
                health = directors_health.probe_all()
                tokens = token_optimizer.tracker.get_stats()
                await websocket.send_json({
                    "event": "orchestra_health_update",
                    "health": health,
                    "tokens": tokens
                })

            elif msg_type == "solo_chat":
                provider = data.get("provider", "gemini")
                prompt = data.get("prompt", "").strip()
                project_path = data.get("project_path") or str(WORKSPACE_DIR)
                options = data.get("options", {})
                if not prompt:
                    continue
                async for ev in orchestra_coordinator.run_solo(provider, prompt, project_path, options):
                    await websocket.send_json(ev)

            elif msg_type == "orchestra_run":
                objective = data.get("objective", "").strip()
                project_path = data.get("project_path") or str(WORKSPACE_DIR)
                if not objective:
                    continue
                async for ev in orchestra_coordinator.run_orchestra(project_path, objective):
                    await websocket.send_json(ev)

            elif msg_type == "chat":
                prompt = data.get("prompt", "").strip()
                options = data.get("options", {})
                
                # Modelo prioritario: Gemini 3.8 Flash High solicitado por el usuario
                target_model = options.get("model") or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
                if "flash" in target_model.lower() or "3.8" in target_model or "2.0" in target_model:
                    target_model = "gemini-3.8-flash"

                temp = float(options.get("temperature", 0.2))
                strict = options.get("strict", True)
                thinking_budget = int(options.get("thinking") or os.environ.get("GEMINI_THINKING_BUDGET", "2048"))
                if not prompt:
                    continue

                await websocket.send_json({"event": "chat_thinking", "prompt": prompt, "model": "Gemini 3.8 Flash High"})

                gemini_key = os.environ.get("GEMINI_API_KEY")

                # Si no hay GEMINI_API_KEY, procesar con el motor local de Antigravity PC
                if not gemini_key:
                    # Ejecución asistida por PC
                    cmd = prompt
                    is_cmd = any(prompt.startswith(p) for p in ["git ", "dir", "ls", "python", "gh ", "echo", "cat", "cd "])
                    if is_cmd:
                        proc = await asyncio.create_subprocess_shell(
                            f"powershell -Command {json.dumps(cmd)}",
                            cwd=str(WORKSPACE_DIR),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await proc.communicate()
                        out_text = (stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")).strip()
                        res_text = out_text or f"Comando ejecutado con éxito (código {proc.returncode})."
                    else:
                        res_text = (
                            f"⚡ Antigravity PC [david.chavez.nge@gmail.com | @zero-phoenix]:\n"
                            f"He recibido tu instrucción: \"{prompt}\".\n"
                            f"La PC anfitriona está vinculada. Puedes ejecutar comandos en tiempo real, "
                            f"explorar repositorios de GitHub en la nube y realizar commits directos en RAM."
                        )

                    # Streaming fluido token a token al celular
                    words = res_text.split(" ")
                    for i in range(0, len(words), 3):
                        chunk_str = " ".join(words[i:i+3]) + " "
                        await websocket.send_json({"event": "chat_chunk", "text": chunk_str})
                        await asyncio.sleep(0.015)

                    await websocket.send_json({"event": "chat_response", "text": res_text})
                    continue

                # Ejecutar consulta con Gemini 3.8 Flash High y Cloud Tools
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

                    def inspect_system_telemetry() -> Dict[str, Any]:
                        """
                        Inspecciona la telemetría en tiempo real de la PC anfitriona (Windows):
                        uso de CPU (%), uso y total de memoria RAM (GB), estado de energía y batería.
                        """
                        return get_system_telemetry()

                    client = genai.Client(api_key=gemini_key)
                    tools = [
                        cloud_inspector.cloud_list_repositories,
                        cloud_inspector.cloud_get_tree,
                        cloud_inspector.cloud_read_file,
                        cloud_inspector.cloud_search_code,
                        cloud_inspector.cloud_compare_files,
                        cloud_inspector.cloud_create_or_update_file,
                        inspect_system_telemetry,
                        delegate_to_desktop,
                    ]

                    # Mapeo de ejecución local
                    active_tools_map = dict(cloud_inspector.CLOUD_TOOLS_MAP)
                    active_tools_map["inspect_system_telemetry"] = inspect_system_telemetry
                    active_tools_map["delegate_to_desktop"] = delegate_to_desktop

                    system_instruction = (
                        "Eres Antigravity Mobile Hub Supremo impulsado por Google Gemini 3.8 Flash High. "
                        "El usuario te habla desde su teléfono Android conectado a su cuenta de GitHub (zero-phoenix) y su PC anfitriona Windows. "
                        "Tienes acceso a inspeccionar repositorios en la nube (cloud_*) propios y de terceros, crear o actualizar archivos y commits directos "
                        "mediante cloud_create_or_update_file, inspeccionar la salud del equipo mediante inspect_system_telemetry, y DELEGAR comandos "
                        "a la PC de Windows mediante 'delegate_to_desktop' para ejecutar git, compilaciones, tests o inspecciones locales. "
                        "Sé conciso, directo, amigable y sumamente preciso."
                    )
                    if strict:
                        system_instruction += (
                            "\nPOLÍTICA ESTRICTA DE GROUNDING: Tienes terminantemente prohibido inventar código o asumir APIs inexistentes. "
                            "Básate EXCLUSIVAMENTE en lo verificado a través de las herramientas de inspección o comandos de la PC. "
                            "Cita siempre archivo y línea de referencia si analizas código."
                        )

                    chat = client.chats.create(
                        model=target_model,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temp,
                            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
                            tools=tools,
                        )
                    )

                    # Envío con reintentos para soportar picos transitorios de demanda (503)
                    response = None
                    for attempt in range(3):
                        try:
                            response = await asyncio.to_thread(chat.send_message, prompt)
                            break
                        except Exception as e_send:
                            err_msg = str(e_send)
                            if ("503" in err_msg or "UNAVAILABLE" in err_msg or "demand" in err_msg) and attempt < 2:
                                await asyncio.sleep(1.2)
                                continue
                            raise e_send

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

                        for attempt in range(3):
                            try:
                                response = await asyncio.to_thread(chat.send_message, tool_responses)
                                break
                            except Exception as e_send_tool:
                                err_msg = str(e_send_tool)
                                if ("503" in err_msg or "UNAVAILABLE" in err_msg or "demand" in err_msg) and attempt < 2:
                                    await asyncio.sleep(1.2)
                                    continue
                                raise e_send_tool

                    final_text = response.text or ""
                    # Streaming token a token al celular
                    words = final_text.split(" ")
                    for i in range(0, len(words), 4):
                        chunk_str = " ".join(words[i:i+4]) + " "
                        await websocket.send_json({"event": "chat_chunk", "text": chunk_str})
                        await asyncio.sleep(0.01)

                    GEMINI_HISTORY.insert(0, {
                        "prompt": prompt,
                        "response": final_text,
                        "model": target_model,
                        "time": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    if len(GEMINI_HISTORY) > 100:
                        GEMINI_HISTORY.pop()

                    await websocket.send_json({
                        "event": "chat_response",
                        "text": final_text
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
    Route("/api/telemetry", api_telemetry),
    Route("/api/auth/session", api_auth_session),
    Route("/api/auth/pair", api_auth_pair, methods=["POST"]),
    Route("/api/auth/sync", api_auth_sync, methods=["GET", "POST"]),
    Route("/api/auth/github-device", api_auth_github_device, methods=["POST"]),
    Route("/api/auth/github-poll", api_auth_github_poll, methods=["POST"]),
    Route("/api/repos", api_repos),
    Route("/api/tree", api_tree),
    Route("/api/file", api_file),
    Route("/api/commit", api_commit, methods=["POST"]),
    Route("/api/exec", api_exec, methods=["POST"]),
    Route("/api/antigravity/conversations", api_antigravity_conversations),
    Route("/api/antigravity/conversation", api_antigravity_conversation_detail),
    Route("/api/projects", api_projects),
    Route("/api/projects/switch", api_projects_switch, methods=["POST"]),
    Route("/api/gemini/history", api_gemini_history),
    Route("/api/tunnel/info", api_tunnel_info),
    Route("/api/tunnel/restart", api_tunnel_restart, methods=["POST"]),
    Route("/api/orchestra/health", api_orchestra_health),
    Route("/api/orchestra/tokens", api_orchestra_tokens),
    Route("/api/solo/chat", api_solo_chat, methods=["POST"]),
    Route("/api/orchestra/run", api_orchestra_run, methods=["POST"]),
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
