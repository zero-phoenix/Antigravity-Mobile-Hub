#!/usr/bin/env python3
"""
Auditoría Popperiana (Falsacionismo de Karl Popper)
Batería de pruebas diseñada específicamente para intentar FALSEAR y ROMPER
las asunciones de corrección de la aplicación Antigravity Mobile Hub antes del despliegue.
"""

import os
import sys
import json
import re
import unittest
import pathlib

BASE_DIR = pathlib.Path(__file__).parent.parent.resolve()
APP_DIR = BASE_DIR / "android-app"
SYS_PATH = BASE_DIR / "github-cloud"
sys.path.insert(0, str(SYS_PATH))
sys.path.insert(0, str(BASE_DIR))

import cloud_inspector

class PopperianAuditTestSuite(unittest.TestCase):

    def test_falsify_url_normalizer_edge_cases(self):
        """
        Falsación de la Hipótesis de Normalización:
        ¿Puede una URL malformada, atípica o profunda romper la extracción de repositorio y ruta?
        """
        cases = [
            ("yabausevita", ("zero-phoenix/yabausevita", None)),
            ("vitasdk/vita-headers", ("vitasdk/vita-headers", None)),
            ("https://github.com/vitasdk/vita-headers", ("vitasdk/vita-headers", None)),
            ("https://github.com/vitasdk/vita-headers.git", ("vitasdk/vita-headers", None)),
            ("https://github.com/vitasdk/vita-headers/blob/master/include/vitasdk.h", ("vitasdk/vita-headers", "include/vitasdk.h")),
            ("https://github.com/torvalds/linux/blob/v6.1/Makefile", ("torvalds/linux", "Makefile")),
            ("   vitasdk/vita-toolchain/   ", ("vitasdk/vita-toolchain", None)),
        ]
        for inp, expected in cases:
            repo, path = cloud_inspector.normalize_repo_and_path(inp)
            self.assertEqual(repo, expected[0], f"Fallo al normalizar repo de '{inp}'")
            self.assertEqual(path, expected[1], f"Fallo al extraer ruta de '{inp}'")

    def test_falsify_manifest_integrity(self):
        """
        Falsación de la Hipótesis del Manifiesto Android:
        ¿Cumple con los estándares W3C y Android para instalación Standalone?
        """
        manifest_path = APP_DIR / "manifest.json"
        self.assertTrue(manifest_path.exists(), "manifest.json no existe en android-app")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("name", data)
        self.assertIn("short_name", data)
        self.assertEqual(data.get("display"), "standalone", "Display debe ser standalone para modo app")
        self.assertIn("icons", data)
        self.assertGreaterEqual(len(data["icons"]), 1, "Debe incluir al menos un icono")

    def test_falsify_assets_availability(self):
        """
        Falsación de la Hipótesis de Integridad de Enlaces:
        ¿Falta algún archivo referenciado en el HTML principal?
        ¿Se usan rutas relativas para compatibilidad total con WebView (file:///android_asset/)?
        """
        index_path = APP_DIR / "index.html"
        self.assertTrue(index_path.exists())
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        css_links = re.findall(r'href=["\']([^"\']+\.css)["\']', html)
        js_links = re.findall(r'src=["\']([^"\']+\.js)["\']', html)

        for c in css_links:
            self.assertFalse(c.startswith("/"), f"CSS no debe usar ruta absoluta de raíz en WebView: {c}")
            local_file = APP_DIR / c
            self.assertTrue(local_file.exists(), f"Archivo CSS referenciado no existe: {local_file}")

        for j in js_links:
            self.assertFalse(j.startswith("/"), f"JS no debe usar ruta absoluta de raíz en WebView: {j}")
            local_file = APP_DIR / j
            self.assertTrue(local_file.exists(), f"Archivo JS referenciado no existe: {local_file}")

    def test_falsify_service_worker_routes(self):
        """
        Falsación de la Hipótesis Offline:
        ¿El service-worker cachea los archivos existentes en disco?
        """
        sw_path = APP_DIR / "service-worker.js"
        self.assertTrue(sw_path.exists())
        with open(sw_path, "r", encoding="utf-8") as f:
            sw_text = f.read()

        self.assertIn("addEventListener('fetch'", sw_text)
        self.assertIn("addEventListener('push'", sw_text)

    def test_falsify_xss_protection_in_app_js(self):
        """
        Falsación de la Hipótesis de Inyección:
        ¿app.js contiene la función escapeHTML y la usa para sanitizar contenido?
        """
        app_js_path = APP_DIR / "js" / "app.js"
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()

        self.assertIn("function escapeHTML", app_js, "Falta la función de escape HTML en app.js")
        self.assertIn("escapeHTML(res.content)", app_js, "res.content no está siendo sanitizado")

    def test_falsify_telemetry_schema(self):
        """
        Falsación de la Hipótesis de Telemetría:
        ¿get_system_telemetry() devuelve métricas de CPU y RAM válidas sin excepciones?
        """
        from bridge.gateway import get_system_telemetry
        telem = get_system_telemetry()
        self.assertIsInstance(telem, dict)
        self.assertIn("cpu_percent", telem)
        self.assertIn("ram_percent", telem)
        self.assertIn("ram_total_gb", telem)
        self.assertIn("ram_used_gb", telem)
        self.assertGreaterEqual(telem["ram_total_gb"], 1.0)
        self.assertGreaterEqual(telem["ram_percent"], 0)
        self.assertLessEqual(telem["ram_percent"], 100)

    def test_falsify_supreme_endpoints_registration(self):
        """
        Falsación de la Hipótesis de Enrutamiento Supremo:
        ¿Las rutas /api/telemetry y /api/commit están declaradas en Starlette?
        """
        from bridge.gateway import routes
        path_list = [getattr(r, "path", None) for r in routes]
        self.assertIn("/api/telemetry", path_list, "Ruta /api/telemetry no registrada")
        self.assertIn("/api/commit", path_list, "Ruta /api/commit no registrada")

if __name__ == "__main__":
    if sys.platform == "win32":
        try: sys.stdout.reconfigure(encoding="utf-8")
        except: pass
    print("\n=== EJECUTANDO AUDITORIA POPPERIANA DE ROBUSTEZ ===")
    unittest.main(verbosity=2)
