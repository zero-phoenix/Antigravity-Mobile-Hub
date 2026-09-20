import os
import sys
import re
import json
import time
import shutil
import pathlib
import threading
import subprocess
from typing import Optional, Dict, Any

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
CLOUDFLARED_EXE = TOOLS_DIR / "cloudflared.exe"
STATE_FILE = pathlib.Path(r"C:\Users\D\.gemini\antigravity\tunnel_state.json")
APP_ENDPOINT_FILE = ROOT_DIR / "android-app" / "tunnel_endpoint.json"

class TunnelManager:
    def __init__(self, local_port: int = 8765):
        self.local_port = local_port
        self.process: Optional[subprocess.Popen] = None
        self.tunnel_url: Optional[str] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.last_started = 0
        self.last_error = ""

    def get_binary_path(self) -> Optional[pathlib.Path]:
        if CLOUDFLARED_EXE.exists():
            return CLOUDFLARED_EXE
        system_bin = shutil.which("cloudflared")
        if system_bin:
            return pathlib.Path(system_bin)
        return None

    def start(self, wait_timeout: int = 15) -> Optional[str]:
        """Inicia el túnel Cloudflare hacia el puerto local y espera la URL pública."""
        with self._lock:
            if self.is_running and self.tunnel_url and self.process and self.process.poll() is None:
                return self.tunnel_url

            bin_path = self.get_binary_path()
            if not bin_path:
                self.last_error = "cloudflared.exe no encontrado en tools/ ni en PATH."
                print(f"[TunnelManager] Error: {self.last_error}")
                return None

            self.stop()
            self.tunnel_url = None
            self.last_error = ""
            self.last_started = time.time()

            cmd = [
                str(bin_path),
                "tunnel",
                "--url", f"http://127.0.0.1:{self.local_port}"
            ]

            print(f"[TunnelManager] Lanzando: {' '.join(cmd)}")
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                self.is_running = True
            except Exception as e:
                self.last_error = str(e)
                self.is_running = False
                print(f"[TunnelManager] Fallo al iniciar proceso: {e}")
                return None

            # Hilo de lectura continua
            self._thread = threading.Thread(target=self._read_output_loop, daemon=True)
            self._thread.start()

        # Esperar hasta que se detecte la URL
        start_wait = time.time()
        while time.time() - start_wait < wait_timeout:
            if self.tunnel_url:
                self._save_state()
                self._sync_to_github()
                return self.tunnel_url
            if self.process.poll() is not None:
                self.last_error = f"cloudflared finalizó prematuramente con código {self.process.poll()}"
                break
            time.sleep(0.5)

        return self.tunnel_url

    def _read_output_loop(self):
        url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        while self.is_running and self.process:
            line = self.process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            # print(f"[cloudflared] {line_str}")
            if not self.tunnel_url:
                match = url_regex.search(line_str)
                if match:
                    self.tunnel_url = match.group(0)
                    print(f"\n[TunnelManager] [GLOBAL TUNNEL ACTIVO]: {self.tunnel_url}\n")
                    self._save_state()
                    self._sync_to_github()

        self.is_running = False

    def _save_state(self):
        data = {
            "url": self.tunnel_url,
            "host": self.tunnel_url.replace("https://", "") if self.tunnel_url else "",
            "local_port": self.local_port,
            "is_active": bool(self.tunnel_url),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "token": os.environ.get("ANTIGRAVITY_TOKEN", "antigravity-secret-key")
        }
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            APP_ENDPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
            APP_ENDPOINT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[TunnelManager] Error guardando estado: {e}")

    def _sync_to_github(self):
        """Sincroniza el endpoint global al Gist 5c5190f26171f01e7a596e3fef3af873 para auto-descubrimiento en Japón."""
        if not self.tunnel_url:
            return

        def _do_sync():
            try:
                content = json.dumps({
                    "url": self.tunnel_url,
                    "host": self.tunnel_url.replace("https://", ""),
                    "local_ip": "192.168.18.113",
                    "port": self.local_port,
                    "token": os.environ.get("ANTIGRAVITY_TOKEN", "antigravity-secret-key"),
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }, indent=2)

                temp_file = ROOT_DIR / "tools" / "antigravity_relay.json"
                temp_file.write_text(content, encoding="utf-8")

                gist_id = "5c5190f26171f01e7a596e3fef3af873"
                subprocess.run(
                    ["gh", "gist", "edit", gist_id, str(temp_file)],
                    check=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            except Exception as e:
                pass

        threading.Thread(target=_do_sync, daemon=True).start()

    def get_info(self) -> Dict[str, Any]:
        return {
            "active": bool(self.tunnel_url and self.is_running),
            "url": self.tunnel_url,
            "host": self.tunnel_url.replace("https://", "") if self.tunnel_url else "",
            "local_ip": "192.168.18.113",
            "local_port": self.local_port,
            "last_error": self.last_error,
            "token": os.environ.get("ANTIGRAVITY_TOKEN", "antigravity-secret-key")
        }

    def stop(self):
        with self._lock:
            self.is_running = False
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                self.process = None
            self.tunnel_url = None
            self._save_state()

# Singleton global
tunnel_manager = TunnelManager(local_port=8765)

if __name__ == "__main__":
    print("Iniciando prueba de TunnelManager...")
    url = tunnel_manager.start(wait_timeout=15)
    print("Resultado URL:", url)
    print("Info:", tunnel_manager.get_info())
