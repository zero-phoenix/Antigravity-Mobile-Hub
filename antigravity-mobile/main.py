#!/usr/bin/env python3
"""
Antigravity Mobile CLI — Entry point para Android (Termux) y entornos portátiles.
"""

import sys
import os

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
except ImportError:
    print("[ERROR] Falta instalar dependencias. Ejecuta: pip install -r requirements.txt")
    sys.exit(1)

from agent import AntigravityMobileAgent

console = Console()

def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║             ⚡ ANTIGRAVITY MOBILE CORE ⚡             ║
    ║   Autonomous Agent for Android / Termux Environment   ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")
    console.print("[dim]Comandos: 'salir' / 'exit' para terminar, '/clear' para reiniciar pantalla.[/dim]\n")

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        console.print("[bold red][ERROR][/bold red] Variable GEMINI_API_KEY no definida.")
        console.print("Por favor exporta tu clave ejecutando:")
        console.print("  [cyan]export GEMINI_API_KEY='tu_clave_aqui'[/cyan]")
        console.print("o agrégala a tu [cyan]~/.bashrc[/cyan].")
        sys.exit(1)

    print_banner()

    try:
        agent = AntigravityMobileAgent(model="gemini-2.5-flash")
    except Exception as e:
        console.print(f"[bold red]Error iniciando el agente:[/bold red] {e}")
        sys.exit(1)

    # Si se pasó un comando por argumentos de CLI
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        agent.execute_turn(prompt, print_callback=console.print)
        return

    # Modo interactivo (REPL)
    while True:
        try:
            user_input = console.input("[bold green]antigravity@mobile ➜ [/bold green]").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "salir", "quit"]:
                console.print("[yellow]Sesión finalizada. Hasta luego.[/yellow]")
                break
            if user_input == "/clear":
                console.clear()
                print_banner()
                continue

            agent.execute_turn(user_input, print_callback=console.print)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Interrupción detectada. Saliendo...[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error durante la ejecución:[/bold red] {e}")

if __name__ == "__main__":
    main()
