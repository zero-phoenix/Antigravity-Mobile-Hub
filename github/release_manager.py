#!/usr/bin/env python3
"""
Gestor automatizado de versiones y releases para repositorios de zero-phoenix.
Calcula el siguiente SemVer, extrae commits y publica releases oficiales con GitHub CLI (gh).
"""

import argparse
import json
import re
import subprocess
import sys

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout.strip(), res.stderr.strip(), res.returncode

def parse_semver(tag_str: str):
    """
    Parsea etiquetas de versión tipo v1.2.3 o 1.2.3.
    """
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", tag_str)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None

def bump_semver(major: int, minor: int, patch: int, bump_type: str):
    if bump_type == "major":
        return f"v{major + 1}.0.0"
    elif bump_type == "minor":
        return f"v{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    raise ValueError(f"Tipo de bump no valido: {bump_type}")

def get_latest_tag(repo_full_name: str):
    # 1. Intentar desde releases oficiales
    out, _, code = run_cmd(f'gh release list --repo {repo_full_name} --limit 1')
    if code == 0 and out:
        parts = out.split("\t")
        if len(parts) >= 3:
            return parts[2]
            
    # 2. Intentar desde tags directos de git
    out, _, code = run_cmd(f'gh api repos/{repo_full_name}/tags --jq ".[0].name"')
    if code == 0 and out and out != "null":
        return out
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Automatizador de releases GitHub SemVer")
    parser.add_argument("--repo", help="Nombre del repositorio (ej. yabausevita, SystemHope-ResAdmis)", default="")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="", help="Tipo de incremento SemVer")
    parser.add_argument("--tag", help="Tag personalizado explicito (ej. v1.2.0)")
    parser.add_argument("--title", help="Titulo de la release", default="")
    parser.add_argument("--notes", help="Notas personalizadas de la release", default="")
    parser.add_argument("--draft", action="store_true", help="Crear como borrador (draft)")
    parser.add_argument("--asset", help="Ruta a binario o archivo para adjuntar (ej. .vpk, .zip)", default="")
    args = parser.parse_args()

    print("\n=== GESTOR DE RELEASES Y VERSIONADO GITHUB ===")
    
    repo = args.repo
    if not repo:
        repo = input("Ingresa el nombre del repositorio (ej. yabausevita): ").strip()
    
    if not repo:
        print("[ERROR] Nombre de repositorio requerido.")
        sys.exit(1)
        
    full_repo = f"zero-phoenix/{repo}" if not repo.startswith("zero-phoenix/") else repo
    
    print(f"\n[*] Consultando estado de {full_repo}...")
    latest_tag = get_latest_tag(full_repo)
    print(f"    Ultimo tag / release detectado: {latest_tag or '(Ninguno)'}")

    target_tag = args.tag
    if not target_tag:
        if latest_tag:
            parsed = parse_semver(latest_tag)
            if parsed:
                maj, mi, pa = parsed
                p_bump = bump_semver(maj, mi, pa, "patch")
                m_bump = bump_semver(maj, mi, pa, "minor")
                M_bump = bump_semver(maj, mi, pa, "major")
                
                if args.bump:
                    target_tag = bump_semver(maj, mi, pa, args.bump)
                else:
                    print(f"\nSugerencias de incremento:")
                    print(f" 1. PATCH -> {p_bump}")
                    print(f" 2. MINOR -> {m_bump}")
                    print(f" 3. MAJOR -> {M_bump}")
                    opt = input("Elige una opcion (1-3) o escribe un tag manual: ").strip()
                    if opt == "1": target_tag = p_bump
                    elif opt == "2": target_tag = m_bump
                    elif opt == "3": target_tag = M_bump
                    else: target_tag = opt if opt else p_bump
            else:
                target_tag = input("Escribe el nuevo tag (ej. v1.0.0): ").strip()
        else:
            target_tag = "v1.0.0"

    print(f"\n[✓] Tag objetivo para la nueva version: {target_tag}")

    title = args.title or f"{repo} {target_tag}"
    
    # Construir comando gh release create
    cmd_parts = [
        "gh", "release", "create", target_tag,
        "--repo", full_repo,
        "--title", f'"{title}"'
    ]

    if args.notes:
        cmd_parts.extend(["--notes", f'"{args.notes}"'])
    else:
        cmd_parts.append("--generate-notes")

    if args.draft:
        cmd_parts.append("--draft")

    if args.asset:
        cmd_parts.append(f'"{args.asset}"')

    final_cmd = " ".join(cmd_parts)
    print(f"\n[*] Comando de publicacion preparado:")
    print(f"    {final_cmd}\n")

    confirm = input("¿Deseas ejecutar y publicar este release en GitHub? (s/N): ").strip().lower()
    if confirm in ["s", "si", "y", "yes"]:
        print("[*] Ejecutando publicacion...")
        stdout, stderr, code = run_cmd(final_cmd)
        if code == 0:
            print(f"[✓] Release publicado exitosamente en GitHub:")
            print(f"    {stdout}")
        else:
            print(f"[ERROR] Fallo la publicacion: {stderr}")
    else:
        print("[*] Operacion cancelada por el usuario.")

if __name__ == "__main__":
    main()
