/**
 * Gemini Engine: Control de modelos, Thinking Budget y Grounding Estricto.
 * Actualizado a la familia oficial Gemini 2.0 (Predeterminado: gemini-2.0-flash).
 */

const GeminiEngine = {
  // Configuración actual
  config: {
    model: (function() {
      const saved = localStorage.getItem('gemini_model');
      if (!saved || saved.includes('2.5') || saved.includes('3.8')) {
        return 'gemini-2.0-flash';
      }
      return saved;
    })(),
    thinkingBudget: parseInt(localStorage.getItem('gemini_thinking') || '0', 10), // 0 = Rápido, 2048 = Analítico, 8192 = Deep Research
    temperature: parseFloat(localStorage.getItem('gemini_temp') || '0.2'),
    strictGrounding: localStorage.getItem('gemini_strict') !== 'false', // True por defecto (cero alucinaciones)
    apiKey: localStorage.getItem('gemini_api_key') || ''
  },

  // Modelos oficiales vigentes de Google
  MODELS: [
    { id: 'gemini-2.0-flash', name: '⚡ Gemini 2.0 Flash', desc: 'Ultrarrápido, latencia mínima, streaming token a token (Predeterminado)' },
    { id: 'gemini-2.0-flash-lite', name: '🚀 Gemini 2.0 Flash Lite', desc: 'Máxima eficiencia y velocidad para consultas frecuentes' },
    { id: 'gemini-1.5-flash', name: '⚡ Gemini 1.5 Flash', desc: 'Rápido, versátil y multimodal' },
    { id: 'gemini-1.5-pro', name: '🧠 Gemini 1.5 Pro', desc: 'Razonamiento complejo y contexto extendido' }
  ],

  saveConfig() {
    localStorage.setItem('gemini_model', this.config.model);
    localStorage.setItem('gemini_thinking', this.config.thinkingBudget);
    localStorage.setItem('gemini_temp', this.config.temperature);
    localStorage.setItem('gemini_strict', this.config.strictGrounding);
  },

  getSystemInstruction() {
    let base = "Eres el asistente de ingeniería Antigravity en Android. Sé directo, técnico y conciso. ";
    if (this.config.strictGrounding) {
      base += "POLÍTICA ESTRICTA DE GROUNDING: Tienes prohibido inventar código, funciones o rutas. " +
              "Básate EXCLUSIVAMENTE en el código o información recuperada de los repositorios de GitHub " +
              "o del sistema anfitrión. Si no sabes algo, indica que el archivo debe ser inspeccionado. " +
              "Siempre que sea posible cita el nombre del archivo y número de línea.";
    }
    return base;
  },

  /**
   * Envía un prompt a través del Gateway de la PC o directamente a Gemini API
   */
  async sendMessage(prompt, onEventCallback) {
    // Si hay WebSocket activo hacia la PC, enviar por el WebSocket para streaming rápido y Cloud Tools
    if (BridgeClient.isConnected()) {
      BridgeClient.sendChatPrompt(prompt, {
        model: this.config.model,
        temperature: this.config.temperature,
        thinking: this.config.thinkingBudget,
        strict: this.config.strictGrounding
      });
      return;
    }

    // Si no está conectado por WebSocket, intentar reconectar o procesar con el backend local
    onEventCallback({ event: 'chat_thinking', prompt: prompt });

    try {
      // Intentar enviar al endpoint HTTP de ejecución de Antigravity
      const bridgeToken = localStorage.getItem('bridge_token') || 'antigravity-secret-key';
      const resp = await fetch('/api/exec', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Antigravity-Token': bridgeToken
        },
        body: JSON.stringify({ command: prompt })
      });

      if (resp.ok) {
        const data = await resp.json();
        const text = data.stdout || data.stderr || `Comando ejecutado con código ${data.exit_code}`;
        onEventCallback({ event: 'chat_response', text: text });
      } else {
        onEventCallback({
          event: 'chat_error',
          message: 'Sin enlace con Antigravity PC. Conéctate al Gateway en Ajustes mediante tu Código PIN.'
        });
      }
    } catch (e) {
      onEventCallback({
        event: 'chat_error',
        message: 'No hay conexión con la PC. Abre Ajustes para sincronizar mediante Código PIN.'
      });
    }
  }
};
