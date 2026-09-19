"""
Motor del agente autónomo Antigravity Mobile.
Implementa el bucle ReAct utilizando el SDK oficial google-genai y llamada a herramientas nativas.
"""

import os
import sys
import json
from typing import List, Dict, Any, Callable
from google import genai
from google.genai import types

import tools

SYSTEM_INSTRUCTION = """
Eres Antigravity Mobile, un agente autónomo de ingeniería de software ejecutándote directamente en el dispositivo móvil (Android / Termux).
Tienes acceso completo al sistema de archivos, la consola de comandos de bash y las capacidades de hardware del teléfono (notificaciones, batería, portapapeles, vibración).

Tus principios:
1. Sé directo, técnico y conciso.
2. Si se te pide realizar una tarea, usa tus herramientas (run_command, view_file, write_to_file, replace_file_content) para inspeccionar y ejecutar de inmediato.
3. Cuando concluyas una tarea larga o crítica, puedes notificar al usuario enviando una notificación nativa al teléfono con mobile_notification o confirmar con mobile_vibrate.
4. Reporta los resultados con honestidad técnica.
"""

# Lista de funciones disponibles para el LLM
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "run_command": tools.run_command,
    "view_file": tools.view_file,
    "write_to_file": tools.write_to_file,
    "replace_file_content": tools.replace_file_content,
    "mobile_notification": tools.mobile_notification,
    "mobile_battery_status": tools.mobile_battery_status,
    "mobile_clipboard": tools.mobile_clipboard,
    "mobile_vibrate": tools.mobile_vibrate,
}

class AntigravityMobileAgent:
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada. Define la variable de entorno.")
        
        self.client = genai.Client()
        self.chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                tools=list(TOOL_FUNCTIONS.values()),
            )
        )

    def execute_turn(self, user_message: str, print_callback=print):
        """
        Ejecuta un turno completo del agente, resolviendo todas las llamadas a herramientas
        en cascada hasta que el modelo produzca una respuesta de texto final.
        """
        print_callback(f"[bold blue]Usuario:[/bold blue] {user_message}")
        
        response = self.chat.send_message(user_message)
        
        max_turns = 15
        turn_count = 0

        while turn_count < max_turns:
            turn_count += 1
            
            # Comprobar si el modelo pidió llamadas a funciones
            function_calls = response.function_calls
            if not function_calls:
                # No hay más herramientas por llamar, el modelo terminó el razonamiento
                print_callback(f"\n[bold green]Antigravity:[/bold green]\n{response.text}\n")
                break

            # Ejecutar cada llamada a función
            tool_responses = []
            for call in function_calls:
                fn_name = call.name
                fn_args = dict(call.args) if call.args else {}
                
                print_callback(f"[bold cyan]⚡ Herramienta ejecutada:[/bold cyan] [yellow]{fn_name}[/yellow]({json.dumps(fn_args, ensure_ascii=False)})")
                
                if fn_name in TOOL_FUNCTIONS:
                    try:
                        result = TOOL_FUNCTIONS[fn_name](**fn_args)
                    except Exception as e:
                        result = {"error": f"Error ejecutando {fn_name}: {str(e)}"}
                else:
                    result = {"error": f"Herramienta desconocida: {fn_name}"}

                # Resumen visual del resultado
                res_str = json.dumps(result, ensure_ascii=False)
                short_res = res_str[:250] + "..." if len(res_str) > 250 else res_str
                print_callback(f"[dim]↳ Resultado:[/dim] {short_res}")
                
                tool_responses.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result}
                    )
                )

            # Enviar el resultado de las herramientas de vuelta a Gemini para continuar
            response = self.chat.send_message(tool_responses)
