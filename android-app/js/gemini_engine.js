/**
 * Gemini Engine: Control de modelos, Thinking Budget y Grounding Estricto.
 */

const GeminiEngine = {
  // Configuración actual
  config: {
    model: localStorage.getItem('gemini_model') || 'gemini-2.5-flash',
    thinkingBudget: parseInt(localStorage.getItem('gemini_thinking') || '0', 10), // 0 = Rápido, 2048 = Analítico, 8192 = Deep Research
    temperature: parseFloat(localStorage.getItem('gemini_temp') || '0.2'),
    strictGrounding: localStorage.getItem('gemini_strict') !== 'false', // True por defecto (cero alucinaciones)
    apiKey: localStorage.getItem('gemini_api_key') || ''
  },

  // Modelos disponibles
  MODELS: [
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', desc: 'Rápido, baja latencia, eficiente' },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', desc: 'Razonamiento profundo y arquitectura' },
    { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash', desc: 'Próxima generación multimodelo' }
  ],

  saveConfig() {
    localStorage.setItem('gemini_model', this.config.model);
    localStorage.setItem('gemini_thinking', this.config.thinkingBudget);
    localStorage.setItem('gemini_temp', this.config.temperature);
    localStorage.setItem('gemini_strict', this.config.strictGrounding);
    localStorage.setItem('gemini_api_key', this.config.apiKey);
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
    // Si hay WebSocket activo hacia la PC, enviar por el WebSocket para usar las herramientas de la PC y Cloud Inspector
    if (BridgeClient.isConnected()) {
      BridgeClient.sendChatPrompt(prompt, {
        model: this.config.model,
        temperature: this.config.temperature,
        thinking: this.config.thinkingBudget,
        strict: this.config.strictGrounding
      });
      return;
    }

    // Fallback directo a Google Gemini API vía HTTPS si no hay conexión local con la PC
    if (!this.config.apiKey) {
      onEventCallback({
        event: 'chat_error',
        message: 'No hay conexión con la PC ni se configuró una GEMINI_API_KEY local en Ajustes.'
      });
      return;
    }

    onEventCallback({ event: 'chat_thinking', prompt: prompt });

    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${this.config.model}:generateContent?key=${this.config.apiKey}`;
      const payload = {
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: this.config.temperature,
        },
        systemInstruction: {
          parts: [{ text: this.getSystemInstruction() }]
        }
      };

      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await resp.json();
      if (data.error) {
        onEventCallback({ event: 'chat_error', message: data.error.message });
      } else {
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '(Sin respuesta)';
        onEventCallback({ event: 'chat_response', text: text });
      }
    } catch (e) {
      onEventCallback({ event: 'chat_error', message: e.message });
    }
  }
};
