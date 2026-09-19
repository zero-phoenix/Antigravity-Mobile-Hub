#!/usr/bin/env python3
"""
Agente Gemini Cloud Inspector:
Permite hacer preguntas sobre cualquier repositorio en la nube a Gemini.
Gemini utiliza las herramientas de cloud_inspector para navegar por los árboles de archivos,
buscar y leer fragmentos de código directamente desde GitHub en RAM sin clonar el repositorio.
"""

import os
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cloud_inspector

SYSTEM_INSTRUCTION = """
Eres un analista de código experto de Antigravity con visión remota sobre repositorios de GitHub.
Tienes acceso a herramientas para:
1. cloud_list_repositories: Ver qué repositorios tiene el usuario en GitHub.
2. cloud_get_tree: Ver la estructura de archivos y carpetas de un repositorio sin descargarlo.
3. cloud_read_file: Leer fragmentos o archivos completos directamente de la nube en memoria RAM.
4. cloud_search_code: Buscar texto, funciones o símbolos en el repositorio remoto.

Cuando el usuario te pregunte por un repositorio:
- Primero inspecciona el árbol o busca archivos relevantes.
- Lee los archivos necesarios en memoria.
- Responde de forma técnica, directa y precisa citando las rutas y líneas encontradas.
- No inventes archivos ni código; básate únicamente en lo que lees de la nube.
"""

def query_gemini_cloud(prompt: str, print_callback=print) -> str:
    from google import genai
    from google.genai import types

    # Herramientas expuestas al modelo
    tools = [
        cloud_inspector.cloud_list_repositories,
        cloud_inspector.cloud_get_tree,
        cloud_inspector.cloud_read_file,
        cloud_inspector.cloud_search_code,
    ]

    client = genai.Client()
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            tools=tools,
        )
    )

    print_callback(f"\n[Prompt] {prompt}")
    response = chat.send_message(prompt)

    turns = 0
    while turns < 10:
        turns += 1
        if not response.function_calls:
            final_text = response.text or ""
            print_callback(f"\n[Gemini Cloud Answer]\n{final_text}\n")
            return final_text

        tool_responses = []
        for call in response.function_calls:
            fn_name = call.name
            fn_args = dict(call.args) if call.args else {}
            print_callback(f"[*] Gemini llamando herramienta cloud: {fn_name}({json.dumps(fn_args, ensure_ascii=False)})")

            if fn_name in cloud_inspector.CLOUD_TOOLS_MAP:
                result = cloud_inspector.CLOUD_TOOLS_MAP[fn_name](**fn_args)
            else:
                result = {"error": f"Herramienta desconocida: {fn_name}"}

            tool_responses.append(
                types.Part.from_function_response(
                    name=fn_name,
                    response={"result": result}
                )
            )

        response = chat.send_message(tool_responses)

    return response.text or ""

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        user_prompt = "Lista mis repositorios en la nube y explícame qué hace yabausevita según su CMakeLists.txt"

    if not os.environ.get("GEMINI_API_KEY"):
        print("[!] GEMINI_API_KEY no detectada. Por favor configúrala con .\\gemini\\setup_key.ps1")
        sys.exit(1)

    query_gemini_cloud(user_prompt)
