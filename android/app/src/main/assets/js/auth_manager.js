/**
 * AuthManager: Gestión de autenticación por Código Móvil, PIN y sincronización con PC.
 * Cero ingreso manual de API Keys.
 */

const AuthManager = {
  state: {
    googleAccount: localStorage.getItem('google_account') || 'david.chavez.nge@gmail.com',
    googleStatus: localStorage.getItem('google_status') || 'authenticated',
    githubUser: localStorage.getItem('github_user') || 'zero-phoenix',
    githubStatus: localStorage.getItem('github_status') || 'authenticated',
    githubToken: localStorage.getItem('github_token') || '',
    bridgeToken: localStorage.getItem('bridge_token') || 'antigravity-secret-key',
  },

  init() {
    this.checkSession();
    this.updateUI();
  },

  async checkSession() {
    try {
      const resp = await fetch(BridgeClient.apiUrl('/api/auth/session'), { cache: 'no-store' });
      if (resp.ok) {
        const data = await resp.json();
        this.state.googleAccount = data.google_account || 'david.chavez.nge@gmail.com';
        this.state.googleStatus = data.google_status || 'authenticated';
        this.state.githubUser = data.github_user || 'zero-phoenix';
        this.state.githubStatus = data.github_status || 'authenticated';
        this.saveState();
        this.updateUI();
        return data;
      }
    } catch (e) {
      // Modo offline o directo
    }
    this.updateUI();
    return null;
  },

  async pairWithPin(pin) {
    try {
      const resp = await fetch(BridgeClient.apiUrl('/api/auth/pair'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pin })
      });
      const data = await resp.json();
      if (data.status === 'success') {
        this.state.googleAccount = data.google_account;
        this.state.googleStatus = 'authenticated';
        this.state.githubUser = data.github_user;
        this.state.githubStatus = 'authenticated';
        if (data.github_token) {
          this.state.githubToken = data.github_token;
        }
        this.state.bridgeToken = data.token;
        this.saveState();
        this.updateUI();
        return { success: true, message: data.message };
      }
      return { success: false, message: data.message || 'PIN inválido' };
    } catch (e) {
      return { success: false, message: 'Error de conexión: ' + e.message };
    }
  },

  async syncFromPC() {
    try {
      const resp = await fetch(BridgeClient.apiUrl('/api/auth/sync?token=' + encodeURIComponent(this.state.bridgeToken)), { cache: 'no-store' });
      if (resp.ok) {
        const data = await resp.json();
        this.state.googleAccount = data.google_account || 'david.chavez.nge@gmail.com';
        this.state.googleStatus = 'authenticated';
        this.state.githubUser = data.github_user || 'zero-phoenix';
        this.state.githubStatus = 'authenticated';
        if (data.github_token) {
          this.state.githubToken = data.github_token;
        }
        this.saveState();
        this.updateUI();
        return { success: true, user: this.state.githubUser, email: this.state.googleAccount };
      }
    } catch (e) {
      return { success: false, message: e.message };
    }
    return { success: false, message: 'No se pudo sincronizar' };
  },

  saveState() {
    localStorage.setItem('google_account', this.state.googleAccount);
    localStorage.setItem('google_status', this.state.googleStatus);
    localStorage.setItem('github_user', this.state.githubUser);
    localStorage.setItem('github_status', this.state.githubStatus);
    if (this.state.githubToken) localStorage.setItem('github_token', this.state.githubToken);
    localStorage.setItem('bridge_token', this.state.bridgeToken);
  },

  updateUI() {
    const googleBadge = document.getElementById('google-account-badge');
    const googleEmail = document.getElementById('google-account-email');
    if (googleBadge && googleEmail) {
      if (this.state.googleStatus === 'authenticated' && this.state.googleAccount) {
        googleBadge.textContent = '🟢 Conectado';
        googleBadge.className = 'status-badge online';
        googleEmail.textContent = this.state.googleAccount;
      } else {
        googleBadge.textContent = '⚪ Desconectado';
        googleBadge.className = 'status-badge offline';
        googleEmail.textContent = 'Sin vincular';
      }
    }

    const githubBadge = document.getElementById('github-account-badge');
    const githubName = document.getElementById('github-account-name');
    if (githubBadge && githubName) {
      if (this.state.githubStatus === 'authenticated' && this.state.githubUser) {
        githubBadge.textContent = '🟢 Conectado';
        githubBadge.className = 'status-badge online';
        githubName.textContent = '@' + this.state.githubUser;
      } else {
        githubBadge.textContent = '⚪ Desconectado';
        githubBadge.className = 'status-badge offline';
        githubName.textContent = 'Sin vincular';
      }
    }
  }
};
