/**
 * App Controller: Orquestador general de UI, eventos, escala de fuentes y navegación.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar Escala de Fuentes y Configuración Guardada
  initFontScale();
  initModelSelector();

  // 2. Inicializar Puente con la PC
  BridgeClient.on(handleBridgeEvents);
  BridgeClient.init();

  // 3. Registrar Service Worker para PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  }

  // 4. Cargar Repositorios Iniciales si es necesario
  loadReposList();
});

// ==============================================================================
// Navegación de Pestañas
// ==============================================================================

function switchTab(viewId, btnEl) {
  document.querySelectorAll('.view-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-tab-btn').forEach(el => el.classList.remove('active'));

  const target = document.getElementById(viewId);
  if (target) target.classList.add('active');
  if (btnEl) btnEl.classList.add('active');

  if (viewId === 'view-repos') {
    loadReposList();
  }
}

// ==============================================================================
// Control de Tamaño de Interfaz y Tipografía
// ==============================================================================

function initFontScale() {
  const savedScale = localStorage.getItem('app_font_scale') || '1';
  setFontScale(savedScale, false);

  const savedCodeScale = localStorage.getItem('app_code_scale') || '1';
  setCodeFontScale(savedCodeScale, false);
}

function setFontScale(scale, save = true) {
  document.documentElement.style.setProperty('--font-scale', scale);
  if (save) localStorage.setItem('app_font_scale', scale);

  document.querySelectorAll('.ui-size-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.scale === scale);
  });
}

function setCodeFontScale(scale, save = true) {
  document.documentElement.style.setProperty('--code-font-scale', scale);
  if (save) localStorage.setItem('app_code_scale', scale);

  document.querySelectorAll('.code-size-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.scale === scale);
  });
}

// ==============================================================================
// Control de Modelos, Thinking Budget y Grounding
// ==============================================================================

function initModelSelector() {
  updateModelPillLabel();
  updateThinkingPillLabel();
  updateGroundingUI();
}

function updateModelPillLabel() {
  const pill = document.getElementById('pill-model-name');
  if (pill) {
    const m = GeminiEngine.MODELS.find(x => x.id === GeminiEngine.config.model);
    pill.innerText = m ? m.name : GeminiEngine.config.model;
  }
}

function cycleModel() {
  const models = GeminiEngine.MODELS.map(m => m.id);
  const idx = models.indexOf(GeminiEngine.config.model);
  const nextIdx = (idx + 1) % models.length;
  GeminiEngine.config.model = models[nextIdx];
  GeminiEngine.saveConfig();
  updateModelPillLabel();
}

function updateThinkingPillLabel() {
  const pill = document.getElementById('pill-thinking-mode');
  if (pill) {
    const budget = GeminiEngine.config.thinkingBudget;
    if (budget === 0) pill.innerText = '⚡ Rápido (0)';
    else if (budget <= 2048) pill.innerText = '🧠 Analítico (2k)';
    else pill.innerText = '🔬 Deep Research (8k)';
  }
}

function cycleThinkingMode() {
  const budgets = [0, 2048, 8192];
  const idx = budgets.indexOf(GeminiEngine.config.thinkingBudget);
  const nextIdx = (idx + 1) % budgets.length;
  GeminiEngine.config.thinkingBudget = budgets[nextIdx];
  GeminiEngine.saveConfig();
  updateThinkingPillLabel();
}

function toggleGrounding() {
  GeminiEngine.config.strictGrounding = !GeminiEngine.config.strictGrounding;
  GeminiEngine.saveConfig();
  updateGroundingUI();
}

function updateGroundingUI() {
  const el = document.getElementById('grounding-badge');
  if (el) {
    el.classList.toggle('active', GeminiEngine.config.strictGrounding);
    el.innerHTML = GeminiEngine.config.strictGrounding 
      ? '🛡️ Grounding: Estricto' 
      : '⚠️ Grounding: Libre';
  }
}

// ==============================================================================
// Módulo 1: Gemini Chat
// ==============================================================================

function handleSendPrompt() {
  const input = document.getElementById('gemini-prompt-input');
  const prompt = input.value.trim();
  if (!prompt) return;

  appendMessage('user', prompt);
  input.value = '';

  GeminiEngine.sendMessage(prompt, handleBridgeEvents);
}

function escapeHTML(str) {
  if (!str) return '';
  const p = document.createElement('p');
  p.textContent = str;
  return p.innerHTML;
}

function appendMessage(role, text, id = null) {
  const scrollArea = document.getElementById('chat-scroll');
  const div = document.createElement('div');
  div.className = `message-card ${role}`;
  if (id) div.id = id;
  // Permitir formato basico seguro pero sanitizar contenido
  const safeText = escapeHTML(text).replace(/\n/g, '<br>');
  div.innerHTML = safeText;
  scrollArea.appendChild(div);
  scrollArea.scrollTop = scrollArea.scrollHeight;
}

function appendToolCall(toolName, args) {
  const scrollArea = document.getElementById('chat-scroll');
  const div = document.createElement('div');
  div.className = 'message-card tool-event';
  div.innerHTML = `⚡ <b>Tool Invocada:</b> <code>${toolName}</code><br><span style="opacity:0.8;">Args: ${JSON.stringify(args)}</span>`;
  scrollArea.appendChild(div);
  scrollArea.scrollTop = scrollArea.scrollHeight;
}

// ==============================================================================
// Módulo 2: GitHub Cloud Explorer
// ==============================================================================

let currentSelectedRepo = null;

function exploreCustomRepo() {
  const input = document.getElementById('custom-repo-input');
  const val = input.value.trim();
  if (!val) return;
  const { repo } = GitHubEngine.normalizeRepo(val);
  openRepoTree(repo);
}

async function loadReposList(owner = 'zero-phoenix') {
  const container = document.getElementById('repos-container');
  container.innerHTML = `<div style="color:var(--text-muted); padding:10px;">Consultando repositorios de ${owner}...</div>`;

  try {
    const repos = await GitHubEngine.listRepos(owner);
    container.innerHTML = '';
    repos.forEach(r => {
      const fullName = r.full_name || (r.owner ? `${r.owner}/${r.name}` : r.name);
      const card = document.createElement('div');
      card.className = 'card-item';
      card.innerHTML = `
        <div class="card-title-row">
          <span>📦 ${r.name}</span>
          <span style="font-size:0.68rem; color:var(--text-muted);">${r.private ? '🔒 Privado' : '🌐 Público'}</span>
        </div>
        <div class="card-desc">${r.description || 'Sin descripción disponible'}</div>
        <div style="display:flex; gap:6px; margin-top:8px;">
          <button class="btn-action-small" onclick="openRepoTree('${fullName}')">Explorar Árbol</button>
          <button class="btn-action-small" onclick="askGeminiAboutRepo('${fullName}')">Analizar con Gemini</button>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = `<div style="color:var(--danger); padding:10px;">Error al listar repos: ${e.message}</div>`;
  }
}

async function openRepoTree(repoName) {
  currentSelectedRepo = repoName;
  const container = document.getElementById('repos-container');
  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
      <b>📂 ${repoName} (en RAM)</b>
      <button class="btn-action-small" onclick="loadReposList()">← Volver</button>
    </div>
    <div id="tree-loader" style="color:var(--text-muted);">Cargando árbol de archivos sin descargar...</div>
    <div id="tree-files-list"></div>
    <div id="file-code-modal" style="display:none; margin-top:12px;"></div>
  `;

  try {
    const tree = await GitHubEngine.getTree(repoName);
    document.getElementById('tree-loader').remove();
    const listEl = document.getElementById('tree-files-list');

    tree.files.forEach(f => {
      const item = document.createElement('div');
      item.style.padding = '6px 8px';
      item.style.borderBottom = '1px solid var(--border-subtle)';
      item.style.fontSize = 'var(--code-font-size)';
      item.style.fontFamily = 'var(--font-mono)';
      item.style.display = 'flex';
      item.style.justifyContent = 'space-between';
      item.innerHTML = `
        <span style="color:var(--accent-cyan); cursor:pointer;" onclick="viewFileInRam('${repoName}', '${f.path}')">📄 ${f.path}</span>
        <span style="color:var(--text-dim); font-size:0.75rem;">${f.size_bytes}B</span>
      `;
      listEl.appendChild(item);
    });
  } catch (e) {
    document.getElementById('tree-files-list').innerHTML = `<div style="color:var(--danger)">Error: ${e.message}</div>`;
  }
}

async function viewFileInRam(repoName, filePath) {
  const modal = document.getElementById('file-code-modal');
  modal.style.display = 'block';
  modal.innerHTML = `<div style="color:var(--text-muted)">Leyendo ${filePath} directamente en memoria...</div>`;

  try {
    const res = await GitHubEngine.readFile(repoName, filePath, 1, 200);
    modal.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-size:0.8rem; font-weight:700; color:#fff;">${filePath} (${res.showing_lines} de ${res.total_lines} líneas)</span>
        <button class="btn-action-small" style="background:var(--accent-indigo);" onclick="sendCodeToGemini('${repoName}', '${filePath}')">Consultar a Gemini</button>
      </div>
      <div class="code-viewer-box">${escapeHTML(res.content)}</div>
    `;
  } catch (e) {
    modal.innerHTML = `<div style="color:var(--danger)">Error al leer archivo: ${e.message}</div>`;
  }
}

function sendCodeToGemini(repoName, filePath) {
  switchTab('view-gemini', document.getElementById('tab-btn-gemini'));
  const prompt = `Analiza en detalle el archivo remoto '${filePath}' del repositorio '${repoName}'. Explica su función y detecta posibles mejoras o bugs.`;
  document.getElementById('gemini-prompt-input').value = prompt;
  handleSendPrompt();
}

function askGeminiAboutRepo(repoName) {
  switchTab('view-gemini', document.getElementById('tab-btn-gemini'));
  const prompt = `Explícame la arquitectura del repositorio en la nube '${repoName}' analizando sus archivos principales.`;
  document.getElementById('gemini-prompt-input').value = prompt;
  handleSendPrompt();
}

// ==============================================================================
// Módulo 3: PC Remote Terminal
// ==============================================================================

function runTerminalCommand(cmd = null) {
  const input = document.getElementById('terminal-cmd-input');
  const command = cmd || input.value.trim();
  if (!command) return;

  const stream = document.getElementById('term-stream');
  stream.textContent += `\nPS > ${command}\n`;
  stream.scrollTop = stream.scrollHeight;

  BridgeClient.sendTerminalCommand(command);
  if (!cmd) input.value = '';
}

function clearTerminal() {
  document.getElementById('term-stream').textContent = 'PS > Consola reiniciada.\n';
}

// ==============================================================================
// Manejo de Eventos del Puente (WebSocket Streaming)
// ==============================================================================

function handleBridgeEvents(data) {
  const hostBadge = document.getElementById('host-status-dot');
  const hostLabel = document.getElementById('host-status-label');

  if (data.event === 'bridge_connected') {
    if (hostBadge) hostBadge.classList.add('connected');
    if (hostLabel) hostLabel.innerText = 'Enlazado (PC)';
  } else if (data.event === 'bridge_disconnected') {
    if (hostBadge) hostBadge.classList.remove('connected');
    if (hostLabel) hostLabel.innerText = 'Desconectado';
  } else if (data.event === 'stdout_chunk') {
    const term = document.getElementById('term-stream');
    if (term) {
      term.textContent += data.text;
      term.scrollTop = term.scrollHeight;
    }
  } else if (data.event === 'exec_end') {
    const term = document.getElementById('term-stream');
    if (term) {
      term.textContent += `\n[Finalizado. Código: ${data.exit_code}]\n`;
      if (data.stderr) term.textContent += `STDERR:\n${data.stderr}\n`;
      term.scrollTop = term.scrollHeight;
    }
  } else if (data.event === 'chat_thinking') {
    appendMessage('gemini', '<i>Pensando e inspeccionando herramientas...</i>', 'thinking-bubble');
  } else if (data.event === 'chat_tool_call') {
    appendToolCall(data.tool, data.args);
  } else if (data.event === 'chat_response') {
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) bubble.remove();
    appendMessage('gemini', data.text);
  } else if (data.event === 'chat_error') {
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) bubble.remove();
    appendMessage('gemini', `<span style="color:var(--danger)">[Error] ${data.message}</span>`);
  }
}

// ==============================================================================
// Módulo 4: Ajustes
// ==============================================================================

function saveSettings() {
  const host = document.getElementById('input-bridge-host').value.trim();
  const token = document.getElementById('input-bridge-token').value.trim();
  const geminiKey = document.getElementById('input-gemini-key').value.trim();
  const ghToken = document.getElementById('input-github-token').value.trim();

  if (host) localStorage.setItem('bridge_host', host);
  if (token) localStorage.setItem('bridge_token', token);
  if (geminiKey) GeminiEngine.config.apiKey = geminiKey;
  if (ghToken) GitHubEngine.saveToken(ghToken);

  GeminiEngine.saveConfig();
  BridgeClient.serverHost = host;
  BridgeClient.token = token;
  BridgeClient.connect();

  alert('Ajustes guardados correctamente. Reconectando...');
}
