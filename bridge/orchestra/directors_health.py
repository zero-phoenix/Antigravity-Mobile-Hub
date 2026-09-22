"""
Directors Health & Circuit Breakers (MAGI-Orchestra)
Monitorea la disponibilidad de los ejecutores en Windows:
- Gemini 3.8 Flash High (API)
- Claude Code CLI (claude.cmd)
- ChatGPT / Codex CLI (codex.cmd)
- ZCode Desktop / Projects
- GitHub CLI (gh.exe)
Implementa cortacircuitos (circuit breakers) y failover automático.
"""

import os
import shutil
import subprocess
import time
import pathlib
from typing import Dict, Any

# Cargar .env si existe
_env_path = pathlib.Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k and not os.environ.get(k):
                os.environ[k] = v

if not os.environ.get("GEMINI_API_KEY"):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            val, _ = winreg.QueryValueEx(key, "GEMINI_API_KEY")
            if val:
                os.environ["GEMINI_API_KEY"] = val
    except Exception:
        pass

class DirectorsHealth:
    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 60 # 60 segundos de caché
        self._breakers = {
            "gemini": {"failures": 0, "opened_at": 0},
            "claude": {"failures": 0, "opened_at": 0},
            "codex": {"failures": 0, "opened_at": 0},
            "zcode": {"failures": 0, "opened_at": 0},
            "gh": {"failures": 0, "opened_at": 0},
        }

    def _is_breaker_open(self, director: str) -> bool:
        breaker = self._breakers.get(director, {"failures": 0, "opened_at": 0})
        if breaker["opened_at"] > 0:
            if time.time() - breaker["opened_at"] < 600: # 10 min de enfriamiento
                return True
            else:
                breaker["opened_at"] = 0
                breaker["failures"] = 0
        return False

    def record_failure(self, director: str):
        if director in self._breakers:
            self._breakers[director]["failures"] += 1
            if self._breakers[director]["failures"] >= 3:
                self._breakers[director]["opened_at"] = time.time()

    def record_success(self, director: str):
        if director in self._breakers:
            self._breakers[director]["failures"] = 0
            self._breakers[director]["opened_at"] = 0

    def probe_all(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and (now - self._cache_time < self._cache_ttl) and self._cache:
            return self._cache

        status = {}

        # 1. Google Gemini 3.8 Flash High
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        status["gemini"] = {
            "id": "gemini",
            "displayName": "Google Gemini 3.8 Flash High",
            "role": "Director & Maestro de Orquesta",
            "available": bool(gemini_key),
            "version": "gemini-3.8-flash (thinking=2048)",
            "breaker_open": self._is_breaker_open("gemini"),
            "note": "Activo y autenticado" if gemini_key else "Requiere GEMINI_API_KEY",
        }

        # 2. Claude Code CLI
        claude_avail = False
        claude_ver = ""
        if not self._is_breaker_open("claude"):
            try:
                res = subprocess.run(
                    ["claude.cmd", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True,
                )
                if res.returncode == 0:
                    claude_avail = True
                    claude_ver = res.stdout.strip()
                    self.record_success("claude")
                else:
                    self.record_failure("claude")
            except Exception:
                self.record_failure("claude")

        status["claude"] = {
            "id": "claude",
            "displayName": "Claude Code CLI",
            "role": "Solista de Arquitectura & Código Crítico",
            "available": claude_avail,
            "version": claude_ver or "No detectado",
            "breaker_open": self._is_breaker_open("claude"),
            "note": "Operacional en Windows" if claude_avail else "Inactivo o en enfriamiento",
        }

        # 3. ChatGPT / Codex CLI
        codex_avail = False
        codex_ver = ""
        if not self._is_breaker_open("codex"):
            try:
                res = subprocess.run(
                    ["codex.cmd", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True,
                )
                if res.returncode == 0:
                    codex_avail = True
                    codex_ver = res.stdout.strip()
                    self.record_success("codex")
                else:
                    self.record_failure("codex")
            except Exception:
                self.record_failure("codex")

        status["codex"] = {
            "id": "codex",
            "displayName": "ChatGPT / Codex CLI",
            "role": "Solista de Productividad & Boilerplate Masivo",
            "available": codex_avail,
            "version": codex_ver or "No detectado",
            "breaker_open": self._is_breaker_open("codex"),
            "note": "Operacional en Windows" if codex_avail else "Inactivo o en enfriamiento",
        }

        # 4. ZCode Desktop / Projects
        zcode_dir = r"C:\Users\D\ZCodeProject"
        zcode_avail = os.path.isdir(zcode_dir)
        status["zcode"] = {
            "id": "zcode",
            "displayName": "ZCode Desktop / ResAdmi",
            "role": "Solista Documental & Automatización de Escritorio",
            "available": zcode_avail,
            "version": "SystemHope ResAdmi Engine",
            "breaker_open": False,
            "note": "Directorio detectado" if zcode_avail else "Directorio no encontrado",
        }

        # 5. GitHub CLI
        gh_avail = bool(shutil.which("gh"))
        status["gh"] = {
            "id": "gh",
            "displayName": "GitHub CLI",
            "role": "Operaciones Remotas de Repositorios",
            "available": gh_avail,
            "version": "gh CLI activo" if gh_avail else "No encontrado",
            "breaker_open": False,
            "note": "Disponible para clones y sync" if gh_avail else "gh no en PATH",
        }

        self._cache = status
        self._cache_time = now
        return status

directors_health = DirectorsHealth()
