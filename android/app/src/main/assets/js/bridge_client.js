/**
 * Bridge Client: Enlace WebSocket y HTTP adaptativo para PC Local (Wi-Fi Perú)
 * y Acceso Global Remoto por Túnel Cloudflare (Japón, 5G, Datos Móviles, Cualquier Red).
 */

const BridgeClient = {
  ws: null,
  token: localStorage.getItem('bridge_token') || 'antigravity-secret-key',
  connected: false,
  eventListeners: [],
  reconnectAttempts: 0,
  discoveryInProgress: false,

  cleanHost(input) {
    if (!input) return '';
    let cleaned = input.trim();
    cleaned = cleaned.replace(/^https?:\/\//i, '');
    cleaned = cleaned.replace(/^wss?:\/\//i, '');
    cleaned = cleaned.replace(/\/.*$/, '');
    return cleaned;
  },

  isRemoteHost(host) {
    if (!host) return false;
    const clean = this.cleanHost(host).toLowerCase();
    return clean.includes('.trycloudflare.com') ||
           clean.includes('.ngrok') ||
           clean.includes('.loca.lt') ||
           clean.includes('.tailscale.net') ||
           (!clean.match(/^\d+\.\d+\.\d+\.\d+(:\d+)?$/) && clean.includes('.'));
  },

  getHost() {
    let h = localStorage.getItem('bridge_host');
    if (!h || h === '127.0.0.1:8765' || h === 'localhost:8765' || h.includes('localhost')) {
      if (window.location.host && window.location.host.length > 0 && !window.location.host.includes('localhost')) {
        h = window.location.host;
      } else {
        h = '192.168.18.113:8765'; // IP Wi-Fi local por defecto en Perú
      }
      localStorage.setItem('bridge_host', h);
    }
    return this.cleanHost(h);
  },

  setHost(newHost) {
    const clean = this.cleanHost(newHost);
    if (clean) {
      localStorage.setItem('bridge_host', clean);
      return clean;
    }
    return this.getHost();
  },

  getProtocol() {
    if (window.location.protocol === 'https:' || this.isRemoteHost(this.getHost())) {
      return 'https:';
    }
    return 'http:';
  },

  getWsProtocol() {
    return this.getProtocol() === 'https:' ? 'wss:' : 'ws:';
  },

  getApiBase() {
    const currentHost = this.getHost();
    if ((window.location.protocol === 'http:' || window.location.protocol === 'https:') && window.location.host === currentHost) {
      return '';
    }
    return `${this.getProtocol()}//${currentHost}`;
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

  /**
   * Auto-descubrimiento global de la PC en la nube vía GitHub Gist.
   * Permite que el celular en Japón encuentre la PC en Perú sin configuración manual.
   */
  async autoDiscoverRemoteHost() {
    if (this.discoveryInProgress) return null;
    this.discoveryInProgress = true;
    console.log('[BridgeClient] 🌐 Buscando endpoint global de la PC en GitHub...');

    try {
      // 1. Intentar leer Gist público fijo de Antigravity Relay
      const gistId = '5c5190f26171f01e7a596e3fef3af873';
      const res = await fetch(`https://api.github.com/gists/${gistId}`, {
        headers: { 'Accept': 'application/vnd.github.v3+json' },
        cache: 'no-store'
      });

      if (res.ok) {
        const data = await res.json();
        const fileObj = data.files && (data.files['antigravity_relay.json'] || Object.values(data.files)[0]);
        if (fileObj && fileObj.content) {
          const info = JSON.parse(fileObj.content);
          if (info.host || info.url) {
            const detectedHost = this.cleanHost(info.host || info.url);
            console.log('[BridgeClient] 🚀 PC Remota descubierta:', detectedHost);
            this.setHost(detectedHost);
            if (info.token) {
              this.token = info.token;
              localStorage.setItem('bridge_token', this.token);
            }
            this.discoveryInProgress = false;
            this.connect();
            return { success: true, host: detectedHost, source: 'github_gist', info };
          }
        }
      }
    } catch (e) {
      console.warn('[BridgeClient] Error en auto-descubrimiento vía Gist:', e);
    }

    // 2. Fallback: buscar endpoint bundled local si existe
    try {
      const res = await fetch('tunnel_endpoint.json', { cache: 'no-store' });
      if (res.ok) {
        const info = await res.json();
        if (info.host || info.url) {
          const detectedHost = this.cleanHost(info.host || info.url);
          this.setHost(detectedHost);
          this.discoveryInProgress = false;
          this.connect();
          return { success: true, host: detectedHost, source: 'local_bundle', info };
        }
      }
    } catch (e) {}

    this.discoveryInProgress = false;
    return { success: false, error: 'No se pudo localizar el túnel de la PC.' };
  },

  init() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('token')) {
      this.token = params.get('token');
      localStorage.setItem('bridge_token', this.token);
    }
    if (params.get('host')) {
      this.setHost(params.get('host'));
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
    const wsProto = this.getWsProtocol();
    const wsUrl = `${wsProto}//${host}/ws/stream?token=${encodeURIComponent(this.token)}`;

    console.log(`[BridgeClient] Conectando a (${this.isRemoteHost(host) ? 'Global/Mundial' : 'Local Wi-Fi'}): ${wsUrl}`);

    try {
      this.ws = new WebSocket(wsUrl);
    } catch(e) {
      this.handleConnectionFail(e);
      return;
    }

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectAttempts = 0;
      console.log(`[BridgeClient] ✅ Conectado con éxito a ${host}`);
      this.emit({ event: 'bridge_connected', host: host, isRemote: this.isRemoteHost(host) });
      const dot = document.getElementById('host-status-dot');
      const label = document.getElementById('host-status-label');
      if (dot) {
        dot.className = 'dot online';
        dot.style.background = '#10b981';
      }
      if (label) {
        label.innerText = this.isRemoteHost(host) ? 'Enlace Global (Cloudflare)' : 'Enlace Wi-Fi (PC)';
      }
    };

    this.ws.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data);
        this.emit(payload);
      } catch(e) {
        console.warn('Payload no JSON recibido del puente:', msg.data);
      }
    };

    this.ws.onerror = (e) => {
      this.connected = false;
      this.emit({ event: 'bridge_error', error: e });
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.emit({ event: 'bridge_disconnected' });
      const dot = document.getElementById('host-status-dot');
      const label = document.getElementById('host-status-label');
      if (dot) {
        dot.className = 'dot offline';
        dot.style.background = '#ef4444';
      }
      if (label) label.innerText = 'Reconectando...';
      this.handleConnectionFail();
    };
  },

  handleConnectionFail(e) {
    this.reconnectAttempts++;
    console.warn(`[BridgeClient] Reintento de conexión #${this.reconnectAttempts}`);

    // Si estamos en un host local (192.168...) y falla 2 veces consecutivas (ej. estamos en Japón fuera de casa),
    // activar auto-descubrimiento global por Cloudflare
    if (this.reconnectAttempts >= 2 && !this.isRemoteHost(this.getHost())) {
      console.log('[BridgeClient] Red local no alcanzable. Intentando auto-descubrimiento global...');
      this.autoDiscoverRemoteHost().then(res => {
        if (!res || !res.success) {
          setTimeout(() => this.connect(), 6000);
        }
      });
      return;
    }

    const delay = Math.min(10000, 3000 * this.reconnectAttempts);
    setTimeout(() => this.connect(), delay);
  },

  sendCommand(command) {
    if (!this.isConnected()) {
      alert('Sin conexión activa con la PC. Verifica el modo de conexión en Ajustes.');
      return;
    }
    this.ws.send(JSON.stringify({
      action: 'exec_stream',
      command: command
    }));
  },

  sendChatPrompt(prompt, options = {}) {
    if (!this.isConnected()) {
      alert('Sin conexión activa con la PC. Verifica el modo de conexión en Ajustes.');
      return;
    }
    this.ws.send(JSON.stringify({
      action: 'chat_prompt',
      prompt: prompt,
      options: options
    }));
  },

  async fetchOrchestraHealth() {
    try {
      const res = await fetch(this.apiUrl('/api/orchestra/health'));
      return await res.json();
    } catch (e) {
      console.warn('[BridgeClient] Error fetching orchestra health:', e);
      return null;
    }
  },

  async fetchTokenStats() {
    try {
      const res = await fetch(this.apiUrl('/api/orchestra/tokens'));
      return await res.json();
    } catch (e) {
      console.warn('[BridgeClient] Error fetching token stats:', e);
      return null;
    }
  },

  sendSoloPrompt(provider, prompt, projectPath = '', options = {}) {
    if (!this.isConnected()) {
      alert('Sin conexión activa con la PC. Verifica el modo de conexión en Ajustes.');
      return;
    }
    this.ws.send(JSON.stringify({
      type: 'solo_chat',
      provider: provider,
      prompt: prompt,
      project_path: projectPath,
      options: options
    }));
  },

  sendOrchestraMission(objective, projectPath = '') {
    if (!this.isConnected()) {
      alert('Sin conexión activa con la PC. Verifica el modo de conexión en Ajustes.');
      return;
    }
    this.ws.send(JSON.stringify({
      type: 'orchestra_run',
      objective: objective,
      project_path: projectPath
    }));
  }
};
