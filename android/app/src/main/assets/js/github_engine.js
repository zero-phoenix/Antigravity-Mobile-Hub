/**
 * GitHub Cloud Engine: Navegación universal, búsqueda y lectura en memoria RAM sin descarga.
 * Soporta repositorios propios (zero-phoenix) y de terceros (ej. vitasdk/*, torvalds/*) por URL o slug.
 */

const GitHubEngine = {
  defaultOwner: 'zero-phoenix',
  token: localStorage.getItem('github_token') || '',
  cache: new Map(),

  saveToken(t) {
    this.token = t.trim();
    localStorage.setItem('github_token', this.token);
  },

  normalizeRepo(input) {
    let cleaned = input.trim();
    cleaned = cleaned.replace(/^https?:\/\/github\.com\//, '');
    cleaned = cleaned.replace(/\.git$/, '');
    cleaned = cleaned.replace(/\/$/, '');

    // Si es enlace a archivo: owner/repo/blob/...
    const match = cleaned.match(/^([^/]+)\/([^/]+)\/blob\/[^/]+\/(.+)$/);
    if (match) {
      return { repo: `${match[1]}/${match[2]}`, path: match[3] };
    }

    const parts = cleaned.split('/');
    if (parts.length >= 2) {
      return { repo: `${parts[0]}/${parts[1]}`, path: null };
    } else if (parts.length === 1 && parts[0]) {
      return { repo: `${this.defaultOwner}/${parts[0]}`, path: null };
    }
    return { repo: `${this.defaultOwner}/yabausevita`, path: null };
  },

  async getHeaders() {
    const headers = { 'Accept': 'application/vnd.github.v3+json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  },

  /**
   * Obtiene los repositorios de cualquier usuario u organización
   */
  async listRepos(owner = this.defaultOwner) {
    const cacheKey = `repos_${owner}`;
    if (this.cache.has(cacheKey)) return this.cache.get(cacheKey);

    // Si la PC está conectada, aprovechar el gateway con token de keyring
    if (BridgeClient.isConnected()) {
      try {
        const res = await fetch(`/api/repos?owner=${encodeURIComponent(owner)}&token=${encodeURIComponent(BridgeClient.token)}`);
        if (res.ok) {
          const data = await res.json();
          const list = data.repositories || [];
          this.cache.set(cacheKey, list);
          return list;
        }
      } catch (e) {}
    }

    // Fallback directo a GitHub REST API
    const headers = await this.getHeaders();
    const resp = await fetch(`https://api.github.com/users/${owner}/repos?per_page=60&sort=updated`, { headers });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    const list = await resp.json();
    this.cache.set(cacheKey, list);
    return list;
  },

  /**
   * Obtiene el árbol completo de archivos de cualquier repositorio en la nube
   */
  async getTree(repoNameOrUrl, branch = null) {
    const { repo } = this.normalizeRepo(repoNameOrUrl);
    const cacheKey = `tree_${repo}_${branch || 'default'}`;
    if (this.cache.has(cacheKey)) return this.cache.get(cacheKey);

    if (BridgeClient.isConnected()) {
      try {
        const branchParam = branch ? `&branch=${encodeURIComponent(branch)}` : '';
        const res = await fetch(`/api/tree?repo=${encodeURIComponent(repo)}${branchParam}&token=${encodeURIComponent(BridgeClient.token)}`);
        if (res.ok) {
          const data = await res.json();
          this.cache.set(cacheKey, data);
          return data;
        }
      } catch (e) {}
    }

    // Fallback directo a GitHub API
    const headers = await this.getHeaders();
    let targetBranch = branch;
    if (!targetBranch) {
      const repoMeta = await (await fetch(`https://api.github.com/repos/${repo}`, { headers })).json();
      targetBranch = repoMeta.default_branch || 'main';
    }

    const resp = await fetch(`https://api.github.com/repos/${repo}/git/trees/${targetBranch}?recursive=1`, { headers });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    const data = await resp.json();
    const result = {
      repository: repo,
      branch: targetBranch,
      files: (data.tree || []).filter(i => i.type === 'blob').map(i => ({ path: i.path, size_bytes: i.size }))
    };
    this.cache.set(cacheKey, result);
    return result;
  },

  /**
   * Lee un archivo en memoria RAM directamente de la nube sin escribir en disco
   */
  async readFile(repoNameOrUrl, filePath = '', startLine = 1, endLine = 300) {
    const { repo, path: extractedPath } = this.normalizeRepo(repoNameOrUrl);
    const targetPath = filePath || extractedPath;
    if (!targetPath) throw new Error('Ruta de archivo no especificada');

    const cacheKey = `file_${repo}_${targetPath}_${startLine}_${endLine}`;
    if (this.cache.has(cacheKey)) return this.cache.get(cacheKey);

    if (BridgeClient.isConnected()) {
      try {
        const res = await fetch(`/api/file?repo=${encodeURIComponent(repo)}&path=${encodeURIComponent(targetPath)}&start=${startLine}&end=${endLine}&token=${encodeURIComponent(BridgeClient.token)}`);
        if (res.ok) {
          const data = await res.json();
          this.cache.set(cacheKey, data);
          return data;
        }
      } catch (e) {}
    }

    const headers = await this.getHeaders();
    const resp = await fetch(`https://api.github.com/repos/${repo}/contents/${targetPath.replace(/^\//, '')}`, { headers });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    const data = await resp.json();

    let decoded = '';
    if (data.encoding === 'base64') {
      decoded = decodeURIComponent(escape(atob(data.content.replace(/\s/g, ''))));
    } else {
      decoded = data.content || '';
    }

    const lines = decoded.split(/\r?\n/);
    const s = Math.max(1, startLine);
    const e = Math.min(lines.length, endLine);
    const chunk = lines.slice(s - 1, e);
    const numbered = chunk.map((line, idx) => `${String(idx + s).padStart(4, ' ')} | ${line}`).join('\n');

    const result = {
      repository: repo,
      path: targetPath,
      total_lines: lines.length,
      showing_lines: `${s}-${e}`,
      content: numbered,
      raw_code: chunk.join('\n')
    };
    this.cache.set(cacheKey, result);
    return result;
  }
};
