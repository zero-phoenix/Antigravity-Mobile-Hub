#!/usr/bin/env python3
"""
Test de conectividad y latencia con la API de Google Gemini (SDK google-genai).
"""

import os
import sys
import time

def test_connection():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] Variable de entorno GEMINI_API_KEY no encontrada.")
        print("Ejecuta setup_key.ps1 o define: $env:GEMINI_API_KEY = '<TU_KEY>'")
        sys.exit(1)

    print(f"[✓] GEMINI_API_KEY detectada: {api_key[:6]}...{api_key[-4:]}")
    
    try:
        from google import genai
    except ImportError:
        print("[ERROR] El paquete google-genai no está instalado. Ejecuta: pip install google-genai")
        sys.exit(1)

    client = genai.Client()
    
    # Modelos recomendados para pruebas
    test_models = ["gemini-2.5-flash", "gemini-2.5-pro"]
    
    for model_name in test_models:
        print(f"\n[*] Probando inferencia con modelo: {model_name}...")
        start_time = time.time()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Responde en una sola frase breve confirmando tu conexion con Antigravity."
            )
            elapsed = time.time() - start_time
            print(f"[✓] Éxito ({elapsed:.2f}s):")
            print(f"    Respuesta: {response.text.strip()}")
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                print(f"    Tokens de entrada : {response.usage_metadata.prompt_token_count}")
                print(f"    Tokens de salida  : {response.usage_metadata.candidates_token_count}")
        except Exception as e:
            print(f"[!] Error con {model_name}: {e}")

if __name__ == "__main__":
    test_connection()
