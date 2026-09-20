"""
GitHub Cloud Inspector (Universal Zero-Download Engine with RAM Cache)
Permite a Gemini explorar, buscar, comparar y leer código de cualquier repositorio
(privados de zero-phoenix o públicos/privados de terceros) en memoria RAM,
sin clonar ni descargar nada a disco.
"""

import os
import sys
import json
import re
import time
import base64
import difflib
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_OWNER = "zero-phoenix"

# Caché en memoria RAM (LRU con TTL de 5 minutos para velocidad extrema y ahorro de cuota)
_RAM_CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 300

def _get_from_cache(key: str) -> Optional[Any]:
    if key in _RAM_CACHE:
        timestamp, data = _RAM_CACHE[key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return data
        else:
            del _RAM_CACHE[key]
    return None

def _set_in_cache(key: str, data: Any):
    _RAM_CACHE[key] = (time.time(), data)

def get_github_token() -> str:
    """
    Obtiene el token de GitHub desde el entorno o dinámicamente desde 'gh auth token'.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    try:
        proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return ""

def _github_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """
    Realiza una petición HTTP autenticada a la API REST de GitHub con soporte de caché.
    """
    cache_key = f"{endpoint}?{urllib.parse.urlencode(params or {})}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    url = f"{GITHUB_API_BASE}/{endpoint.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "User-Agent": "Antigravity-UniversalInspector/2.0",
        "Accept": "application/vnd.github.v3+json",
    }
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            parsed = json.loads(data.decode("utf-8"))
            _set_in_cache(cache_key, parsed)
            return parsed
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {e.reason}", "details": error_body}
    except Exception as e:
        return {"error": str(e)}

def normalize_repo_and_path(input_str: str) -> Tuple[str, Optional[str]]:
    """
    Normaliza cualquier formato de repositorio de GitHub:
    - 'yabausevita' -> ('zero-phoenix/yabausevita', None)
    - 'vitasdk/vita-headers' -> ('vitasdk/vita-headers', None)
    - 'https://github.com/vitasdk/vita-headers' -> ('vitasdk/vita-headers', None)
    - 'https://github.com/owner/repo/blob/branch/src/main.c' -> ('owner/repo', 'src/main.c')
    """
    cleaned = input_str.strip()
    # Limpiar prefijos de URL
    cleaned = re.sub(r"^https?://github\.com/", "", cleaned)
    cleaned = re.sub(r"\.git$", "", cleaned)
    cleaned = cleaned.strip("/")

    # Detectar enlaces directos a archivos: owner/repo/blob/branch/path/to/file
    match_file = re.match(r"^([^/]+)/([^/]+)/blob/[^/]+/(.+)$", cleaned)
    if match_file:
        return f"{match_file.group(1)}/{match_file.group(2)}", match_file.group(3)

    parts = cleaned.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}", None
    elif len(parts) == 1 and parts[0]:
        return f"{DEFAULT_OWNER}/{parts[0]}", None
    return f"{DEFAULT_OWNER}/unknown", None

# ==============================================================================
# Herramientas de Inspección Cloud (Gemini Function Calling & CLI)
# ==============================================================================

def cloud_list_repositories(owner: str = DEFAULT_OWNER) -> Dict[str, Any]:
    """
    Lista los repositorios en la nube de cualquier usuario u organización (por defecto zero-phoenix).
    """
    data = _github_request(f"/users/{owner}/repos", {"per_page": 60, "sort": "updated"})
    if isinstance(data, dict) and "error" in data:
        data = _github_request("/user/repos", {"per_page": 60, "sort": "updated"})
        if isinstance(data, dict) and "error" in data:
            return data

    repos = []
    for r in data:
        repos.append({
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "owner": r.get("owner", {}).get("login"),
            "private": r.get("private"),
            "description": r.get("description"),
            "updated_at": r.get("updated_at"),
            "default_branch": r.get("default_branch", "main")
        })
    return {"owner": owner, "total": len(repos), "repositories": repos}

def cloud_get_tree(repo_name_or_url: str, branch: Optional[str] = None, max_entries: int = 300) -> Dict[str, Any]:
    """
    Obtiene el árbol completo de archivos de cualquier repositorio (propio o de un tercero) en la nube en 1 llamada.
    """
    full_repo, _ = normalize_repo_and_path(repo_name_or_url)
    if not branch:
        repo_info = _github_request(f"/repos/{full_repo}")
        if "error" in repo_info:
            return repo_info
        branch = repo_info.get("default_branch", "main")

    data = _github_request(f"/repos/{full_repo}/git/trees/{branch}", {"recursive": "1"})
    if "error" in data:
        return data

    tree = data.get("tree", [])
    files = []
    directories = []

    for item in tree[:max_entries]:
        path = item.get("path")
        itype = item.get("type")
        size = item.get("size", 0)
        if itype == "blob":
            files.append({"path": path, "size_bytes": size})
        elif itype == "tree":
            directories.append(path)

    return {
        "repository": full_repo,
        "branch": branch,
        "total_files": len(files),
        "total_dirs": len(directories),
        "truncated": data.get("truncated", False) or len(tree) > max_entries,
        "files": files,
        "directories": directories[:50]
    }

def cloud_read_file(repo_name_or_url: str, file_path: str = "", branch: Optional[str] = None, start_line: int = 1, end_line: int = 400) -> Dict[str, Any]:
    """
    Lee cualquier archivo de tu cuenta o de cualquier repositorio de un tercero directamente en RAM.
    """
    full_repo, extracted_path = normalize_repo_and_path(repo_name_or_url)
    target_path = file_path or extracted_path
    if not target_path:
        return {"error": "Ruta de archivo no especificada."}

    params = {}
    if branch:
        params["ref"] = branch

    data = _github_request(f"/repos/{full_repo}/contents/{target_path.lstrip('/')}", params)
    if "error" in data:
        return data

    if data.get("type") != "file":
        return {"error": f"'{target_path}' no es un archivo (es {data.get('type')})."}

    encoding = data.get("encoding")
    content_raw = data.get("content", "")

    try:
        if encoding == "base64":
            decoded = base64.b64decode(content_raw).decode("utf-8", errors="replace")
        else:
            decoded = content_raw

        lines = decoded.splitlines(keepends=True)
        total_lines = len(lines)
        s = max(1, start_line)
        e = min(total_lines, end_line)

        selected_lines = lines[s - 1 : e]
        numbered_content = "".join(f"{i + s:4d} | {line}" for i, line in enumerate(selected_lines))

        return {
            "repository": full_repo,
            "path": target_path,
            "size_bytes": data.get("size", 0),
            "total_lines": total_lines,
            "showing_lines": f"{s}-{e}",
            "content": numbered_content,
            "raw_text": decoded
        }
    except Exception as ex:
        return {"error": f"Fallo al decodificar archivo: {str(ex)}"}

def cloud_search_code(repo_name_or_url: str, query: str) -> Dict[str, Any]:
    """
    Busca funciones o palabras clave en cualquier repositorio de GitHub sin clonar.
    """
    full_repo, _ = normalize_repo_and_path(repo_name_or_url)
    search_query = f"{query} repo:{full_repo}"
    data = _github_request("/search/code", {"q": search_query, "per_page": 10})
    if "error" in data:
        return data

    items = []
    for item in data.get("items", []):
        items.append({
            "path": item.get("path"),
            "html_url": item.get("html_url"),
            "score": item.get("score")
        })

    return {
        "repository": full_repo,
        "query": query,
        "total_matches": data.get("total_count", 0),
        "matches": items
    }

def cloud_compare_files(repo_a: str, path_a: str, repo_b: str, path_b: str) -> Dict[str, Any]:
    """
    Compara en memoria RAM dos archivos (por ejemplo, tu repositorio privado vs el de un tercero)
    y genera un diff unificado sin descargar nada.
    """
    res_a = cloud_read_file(repo_a, path_a, start_line=1, end_line=1000)
    if "error" in res_a:
        return {"error": f"Error leyendo {repo_a}/{path_a}: {res_a['error']}"}

    res_b = cloud_read_file(repo_b, path_b, start_line=1, end_line=1000)
    if "error" in res_b:
        return {"error": f"Error leyendo {repo_b}/{path_b}: {res_b['error']}"}

    lines_a = res_a["raw_text"].splitlines()
    lines_b = res_b["raw_text"].splitlines()

    diff = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=f"{res_a['repository']}/{path_a}",
        tofile=f"{res_b['repository']}/{path_b}",
        lineterm=""
    ))

    return {
        "source": f"{res_a['repository']}/{path_a}",
        "target": f"{res_b['repository']}/{path_b}",
        "identical": len(diff) == 0,
        "diff_lines": len(diff),
        "diff": "\n".join(diff[:250])
    }

def cloud_create_or_update_file(repo: str, path: str, content: str, message: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """
    Crea o actualiza un archivo en cualquier repositorio de GitHub directamente desde la memoria RAM,
    generando un nuevo commit sin necesidad de clonar ni descargar el repositorio.
    """
    owner, repo_name = normalize_repo(repo)
    full_repo = f"{owner}/{repo_name}"
    token = get_github_token()
    if not token:
        return {"error": "Se requiere autenticación con GitHub (token no encontrado)"}

    # 1. Obtener SHA previo si el archivo ya existe
    sha = None
    try:
        req = urllib.request.Request(
            f"{GITHUB_API_BASE}/repos/{full_repo}/contents/{path.lstrip('/')}",
            headers={
                "User-Agent": "Antigravity-UniversalInspector/2.0",
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"Bearer {token}",
            }
        )
        if branch:
            req.full_url += f"?ref={urllib.parse.quote(branch)}"
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return {"error": f"Error verificando archivo: HTTP {e.code}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

    # 2. Construir payload de commit
    b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    payload = {
        "message": message or f"update: {path} via Antigravity Mobile Hub",
        "content": b64_content,
    }
    if sha:
        payload["sha"] = sha
    if branch:
        payload["branch"] = branch

    # 3. Enviar PUT a la API de contenidos de GitHub
    try:
        req_put = urllib.request.Request(
            f"{GITHUB_API_BASE}/repos/{full_repo}/contents/{path.lstrip('/')}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": "Antigravity-UniversalInspector/2.0",
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="PUT"
        )
        with urllib.request.urlopen(req_put, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            
            # Invalidar entradas de caché de este archivo y del árbol
            cache_keys_to_delete = [k for k in _RAM_CACHE.keys() if full_repo in k]
            for k in cache_keys_to_delete:
                del _RAM_CACHE[k]

            commit_info = result.get("commit", {})
            return {
                "status": "success",
                "repository": full_repo,
                "path": path,
                "commit_sha": commit_info.get("sha"),
                "commit_message": commit_info.get("message"),
                "html_url": commit_info.get("html_url"),
                "is_update": sha is not None
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"error": f"Fallo al crear commit: {str(e)}"}

# Mapa de herramientas disponibles para Gemini
CLOUD_TOOLS_MAP = {
    "cloud_list_repositories": cloud_list_repositories,
    "cloud_get_tree": cloud_get_tree,
    "cloud_read_file": cloud_read_file,
    "cloud_search_code": cloud_search_code,
    "cloud_compare_files": cloud_compare_files,
    "cloud_create_or_update_file": cloud_create_or_update_file,
}
