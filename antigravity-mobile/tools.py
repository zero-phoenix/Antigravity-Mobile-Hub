"""
Herramientas del agente Antigravity Mobile.
Soporta comandos de shell (Linux/Termux/Windows), gestión de archivos
y llamadas a la API de hardware de Android a través de Termux:API.
"""

import os
import subprocess
import shutil
import json
from typing import Dict, Any, Optional

def run_command(command: str) -> Dict[str, Any]:
    """
    Ejecuta un comando de shell en el sistema operativo / Termux y devuelve el resultado.
    """
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:] if len(proc.stdout) > 8000 else proc.stdout,
            "stderr": proc.stderr[-4000:] if len(proc.stderr) > 4000 else proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "error": "El comando excedió el tiempo límite (120s)."}
    except Exception as e:
        return {"exit_code": -1, "error": str(e)}

def view_file(path: str, start_line: int = 1, end_line: int = 200) -> Dict[str, Any]:
    """
    Lee las líneas especificadas de un archivo de texto en el dispositivo.
    """
    if not os.path.exists(path):
        return {"error": f"El archivo '{path}' no existe."}
    if os.path.isdir(path):
        return {"error": f"'{path}' es un directorio, no un archivo."}

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total = len(lines)
        start = max(1, start_line)
        end = min(total, end_line)
        
        chunk = lines[start - 1 : end]
        content_with_numbers = "".join(f"{i + start}: {line}" for i, line in enumerate(chunk))
        
        return {
            "total_lines": total,
            "showing_lines": f"{start}-{end}",
            "content": content_with_numbers
        }
    except Exception as e:
        return {"error": str(e)}

def write_to_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    Crea o sobrescribe un archivo con el contenido especificado.
    """
    if os.path.exists(path) and not overwrite:
        return {"error": f"El archivo '{path}' ya existe. Especifica overwrite=True para sobrescribirlo."}

    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
            
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "bytes_written": len(content.encode("utf-8")), "path": path}
    except Exception as e:
        return {"error": str(e)}

def replace_file_content(path: str, target: str, replacement: str) -> Dict[str, Any]:
    """
    Reemplaza quirúrgicamente una cadena exacta por otra dentro de un archivo existente.
    """
    if not os.path.exists(path):
        return {"error": f"El archivo '{path}' no existe."}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()

        if target not in data:
            return {"error": "El texto objetivo (target) no fue encontrado exactamente en el archivo."}

        count = data.count(target)
        new_data = data.replace(target, replacement, 1)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_data)

        return {"success": True, "occurrences_found": count, "replaced": 1}
    except Exception as e:
        return {"error": str(e)}

# --- Herramientas Específicas de Hardware Móvil (Termux:API) ---

def mobile_notification(title: str, message: str) -> Dict[str, Any]:
    """
    Envía una notificación nativa al panel de notificaciones de Android.
    """
    termux_notify = shutil.which("termux-notification")
    if not termux_notify:
        return {"status": "Simulada (termux-api no disponible)", "title": title, "message": message}
    
    cmd = f'termux-notification --title "{title}" --content "{message}"'
    res = run_command(cmd)
    return {"status": "Notificación enviada a Android", "result": res}

def mobile_battery_status() -> Dict[str, Any]:
    """
    Consulta el estado de batería del dispositivo móvil (porcentaje, temperatura, cargador).
    """
    termux_battery = shutil.which("termux-battery-status")
    if not termux_battery:
        return {"percentage": 100, "status": "Simulado / Enchufe de desarrollo"}
    
    res = run_command("termux-battery-status")
    if res["exit_code"] == 0 and res["stdout"]:
        try:
            return json.loads(res["stdout"])
        except json.JSONDecodeError:
            return {"raw": res["stdout"]}
    return {"error": res.get("stderr", "No se pudo obtener el estado de la batería")}

def mobile_clipboard(action: str = "get", text: str = "") -> Dict[str, Any]:
    """
    Lee o escribe en el portapapeles del sistema de Android.
    action: 'get' o 'set'
    """
    if action == "get":
        cmd = shutil.which("termux-clipboard-get")
        if not cmd:
            return {"clipboard": "(termux-clipboard no disponible)"}
        res = run_command("termux-clipboard-get")
        return {"clipboard": res["stdout"]}
    elif action == "set":
        cmd = shutil.which("termux-clipboard-set")
        if not cmd:
            return {"status": "Simulado"}
        res = subprocess.run(["termux-clipboard-set"], input=text, text=True, capture_output=True)
        return {"status": "Portapapeles actualizado"}
    return {"error": f"Acción inválida: {action}"}

def mobile_vibrate(duration_ms: int = 300) -> Dict[str, Any]:
    """
    Hace vibrar el teléfono durante la cantidad de milisegundos especificada (confirmación háptica).
    """
    cmd = shutil.which("termux-vibrate")
    if not cmd:
        return {"status": "Simulado (vibración no disponible)"}
    run_command(f"termux-vibrate -d {duration_ms}")
    return {"status": f"Vibración ejecutada ({duration_ms}ms)"}
