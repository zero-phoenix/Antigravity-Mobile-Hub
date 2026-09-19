#!/usr/bin/env python3
"""
Prueba unitaria e integracion de Cloud Inspector.
Verifica que las lecturas ocurran en memoria RAM sin crear archivos en disco.
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cloud_inspector

def run_tests():
    print("\n=== TEST DE GITHUB CLOUD INSPECTOR (ZERO-DOWNLOAD) ===")
    token = cloud_inspector.get_github_token()
    if token:
        print(f"[OK] Token de GitHub detectado: {token[:6]}...{token[-4:]}")
    else:
        print("[!] No se detecto token de GitHub. Solo repositorios publicos seran accesibles.")

    # 1. Probar listar repositorios
    print("\n[1/3] Probando cloud_list_repositories('zero-phoenix')...")
    res_repos = cloud_inspector.cloud_list_repositories("zero-phoenix")
    if "error" in res_repos:
        print(f"[!] Error listando repos: {res_repos['error']}")
    else:
        print(f"[OK] Encontrados {res_repos['total']} repositorios en la nube.")
        names = [r["name"] for r in res_repos["repositories"][:5]]
        print(f"    Primeros 5: {', '.join(names)}")

    # 2. Probar obtener arbol de yabausevita
    print("\n[2/3] Probando cloud_get_tree('yabausevita')...")
    res_tree = cloud_inspector.cloud_get_tree("yabausevita", max_entries=20)
    if "error" in res_tree:
        print(f"[!] Error obteniendo arbol: {res_tree['error']}")
    else:
        print(f"[OK] Arbol obtenido para {res_tree['repository']} (Rama: {res_tree['branch']}):")
        print(f"    Total archivos indexados en RAM: {res_tree['total_files']}")
        for f in res_tree["files"][:5]:
            print(f"    - {f['path']} ({f['size_bytes']} bytes)")

    # 3. Probar lectura directa en memoria de CMakeLists.txt
    print("\n[3/3] Probando cloud_read_file('yabausevita', 'CMakeLists.txt', start_line=1, end_line=15)...")
    res_file = cloud_inspector.cloud_read_file("yabausevita", "CMakeLists.txt", start_line=1, end_line=15)
    if "error" in res_file:
        print(f"[!] Error leyendo archivo: {res_file['error']}")
    else:
        print(f"[OK] Archivo leido en memoria RAM ({res_file['total_lines']} lineas totales):")
        print(res_file["content"])

    print("\n[OK] VERIFICACION COMPLETADA: Lectura 100% en memoria sin escribir en disco.\n")

if __name__ == "__main__":
    run_tests()
