/**
 * Bridge Client: Enlace WebSocket persistente y streaming de terminal remota con la PC.
 */

const BridgeClient = {
  ws: null,
  token: localStorage.getItem('bridge_token') || 'antigravity-secret-key',
  connected: false,
  eventListeners: [],

  getHost() {
    let h = localStorage.getItem('bridge_host');
    if (!h || h === '127.0.0.1:8765' || h === 'localhost:8765' || h.includes('localhost')) {
      if (window.location.host && window.location.host.length > 0 && !window.location.host.includes('localhost')) {
        h = window.location.host;
      } else {
        h = '192.168.18.113:8765'; // IP Wi-Fi de la PC anfitriona
      }
      localStorage.setItem('bridge_host', h);
    }
    return h;
  },

  getApiBase() {
    if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
      return '';
    }
    return `http://${this.getHost()}`;
  },

  apiUrl(path) {
    const base = this.getApiBase();
    const cleanPath = path.startsWith('/') ? path : '/' + path;
    const fullUrl = base ? `${base}${cleanPath}` : cleanPath;
    const token = this.token || localStorage.getItem('bridge_token') || 'antigravity-secret-key';
    if (!fullUrl.includes('token=')) {
      const sep = fullUrl.includes('?') ? '&' : '?';
      return `${fullUrl}${sep}token=${encodeURIComponent(token)}`;
    }
    return fullUrl;
  },

  init() {
    // Si la URL contiene un token o host, capturarlo
    const params = new URLSearchParams(window.location.search);
    if (params.get('token')) {
      this.token = params.get('token');
      localStorage.setItem('bridge_token', this.token);
    }
    if (params.get('host')) {
      localStorage.setItem('bridge_host', params.get('host'));
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

    const host = this.getHost();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}/ws/stream?token=${encodeURIComponent(this.token)}`;

    try {
      this.ws = new WebSocket(wsUrl);
    } catch(e) {
      this.connected = false;
      this.emit({ event: 'bridge_error', error: e });
      setTimeout(() => this.connect(), 4000);
      return;
    }

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
