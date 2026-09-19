#!/usr/bin/env python3
"""
Auditoria completa de repositorios de GitHub para la cuenta zero-phoenix.
Consulta visibilidad, rama por defecto, fecha de actualizacion y ultimos releases/tags.
"""

import json
import subprocess
import sys

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout.strip(), res.stderr.strip(), res.returncode

def main():
    print("\n=== AUDITORIA DE REPOSITORIOS GITHUB (zero-phoenix) ===")
    
    # 1. Obtener lista de repositorios
    cmd = 'gh repo list zero-phoenix --limit 30 --json name,isPrivate,isArchived,description,updatedAt,defaultBranchRef'
    stdout, stderr, code = run_cmd(cmd)
    if code != 0:
        print(f"[ERROR] No se pudo obtener la lista de repositorios: {stderr}")
        sys.exit(1)

    repos = json.loads(stdout)
    
    print(f"[*] Repositorios encontrados: {len(repos)}\n")
    print(f"{'REPOSITORIO':<28} | {'ESTADO':<16} | {'ULTIMO RELEASE / TAG':<25} | {'ACTUALIZADO'}")
    print("-" * 90)

    for r in repos:
        name = r["name"]
        full_name = f"zero-phoenix/{name}"
        vis = "Privado" if r["isPrivate"] else "Publico"
        if r.get("isArchived"):
            vis += " (Arch.)"

        # Consultar ultimo release
        rel_cmd = f'gh release list --repo {full_name} --limit 1'
        rel_out, _, _ = run_cmd(rel_cmd)
        
        last_tag = "(Sin releases)"
        if rel_out:
            parts = rel_out.split("\t")
            if len(parts) >= 3:
                last_tag = f"{parts[2]} ({parts[0]})"
            else:
                last_tag = rel_out.splitlines()[0]
        else:
            # Consultar si hay tags aunque no haya releases
            tag_cmd = f'gh api repos/{full_name}/tags --jq ".[0].name" 2>nul'
            tag_out, _, _ = run_cmd(tag_cmd)
            if tag_out and tag_out != "null":
                last_tag = f"tag: {tag_out}"

        updated = r["updatedAt"][:16].replace("T", " ")
        print(f"{name:<28} | {vis:<16} | {last_tag:<25} | {updated}")

    print("-" * 90)
    print(f"[OK] Total auditados: {len(repos)}\n")

if __name__ == "__main__":
    main()
