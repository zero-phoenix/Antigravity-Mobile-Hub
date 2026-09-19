/**
 * Bridge Client: Enlace WebSocket persistente y streaming de terminal remota con la PC.
 */

const BridgeClient = {
  ws: null,
  token: localStorage.getItem('bridge_token') || 'antigravity-secret-key',
  serverHost: localStorage.getItem('bridge_host') || (window.location.host && window.location.host.length > 0 ? window.location.host : '192.168.18.113:8765'),
  connected: false,
  eventListeners: [],

  init() {
    // Si la URL contiene un token, capturarlo
    const params = new URLSearchParams(window.location.search);
    if (params.get('token')) {
      this.token = params.get('token');
      localStorage.setItem('bridge_token', this.token);
    }
    this.connect();
  },

  isConnected() {
    return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
  },

  on(listener) {
    this.eventListeners.push(listener);
  },

  emit(data) {
    this.eventListeners.forEach(fn => {
      try { fn(data); } catch(e) { console.error(e); }
    });
  },

  connect() {
    if (this.ws) {
      try { this.ws.close(); } catch(e) {}
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = this.serverHost || window.location.host || '127.0.0.1:8765';
    const wsUrl = `${protocol}//${host}/ws/stream?token=${encodeURIComponent(this.token)}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.connected = true;
      this.emit({ event: 'bridge_connected', host: host });
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.emit({ event: 'bridge_disconnected' });
      // Reintentar conexión automáticamente cada 3 segundos
      setTimeout(() => this.connect(), 3500);
    };

    this.ws.onerror = (err) => {
      this.connected = false;
      this.emit({ event: 'bridge_error', error: err });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data);
      } catch(e) {}
    };
  },

  sendTerminalCommand(cmd) {
    if (!this.isConnected()) {
      this.emit({ event: 'stdout_chunk', text: '\n[ERROR] No hay conexión con la PC anfitriona.\n' });
      return;
    }
    this.ws.send(JSON.stringify({ type: 'exec', command: cmd }));
  },

  sendChatPrompt(prompt, options = {}) {
    if (!this.isConnected()) {
      this.emit({ event: 'chat_error', message: 'No hay conexión con la PC. Revisa el enlace en Ajustes.' });
      return;
    }
    this.ws.send(JSON.stringify({
      type: 'chat',
      prompt: prompt,
      options: options
    }));
  }
};
