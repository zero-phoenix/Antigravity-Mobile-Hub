/**
 * App Controller: Orquestador general de UI, eventos, escala de fuentes y navegación.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar Escala de Fuentes y Configuración Guardada
  initFontScale();
  initModelSelector();

  // 2. Inicializar Gestor de Autenticación sin claves manuales
  if (typeof AuthManager !== 'undefined') {
    AuthManager.init();
  }

  // 3. Inicializar Puente con la PC
  BridgeClient.on(handleBridgeEvents);
  BridgeClient.init();

  // 4. Registrar Service Worker para PWA (solo cuando se sirve por HTTP/HTTPS)
  if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('service-worker.js').catch(() => {});
  }

  // 5. Cargar Repositorios Iniciales si es necesario
  loadReposList();

  // 6. Poblar Ajustes de Interfaz
  initSettingsInputs();
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
  } else if (viewId === 'view-conversations') {
    loadConversationsList();
  } else if (viewId === 'view-projects') {
    loadProjectsList();
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
    if (budget === 0) pill.innerText = '⚡ Flash (Rápido)';
    else if (budget <= 2048) pill.innerText = '⚡ Flash High (2k)';
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

function quickPrompt(text) {
  const input = document.getElementById('gemini-prompt-input');
  if (input) {
    input.value = text;
    handleSendPrompt();
  }
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
  if (role === 'gemini' && !id) {
    div.innerHTML = `${safeText} <button class="btn-speak" onclick="speakText(this.parentElement.innerText)" title="Escuchar respuesta">🔊</button>`;
  } else {
    div.innerHTML = safeText;
  }
  scrollArea.appendChild(div);
  scrollArea.scrollTop = scrollArea.scrollHeight;
}

function appendToolCall(toolName, args) {
  const scrollArea = document.getElementById('chat-scroll');
  const div = document.createElement('div');
  div.className = 'message-card tool-event agent-tool-call';
  div.innerHTML = `🛠️ <b>Agente Autónomo:</b> <code>${escapeHTML(toolName)}</code><br><span style="opacity:0.85; font-size:0.7rem;">Args: ${escapeHTML(JSON.stringify(args))}</span>`;
  scrollArea.appendChild(div);
  scrollArea.scrollTop = scrollArea.scrollHeight;
}

// Reconocimiento y Dictado por Voz (Speech-to-Text)
let speechRecognizer = null;
let isListening = false;

function toggleVoiceRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    alert('Reconocimiento de voz no soportado en este entorno de WebView.');
    return;
  }

  const micBtn = document.getElementById('btn-mic');
  if (isListening && speechRecognizer) {
    speechRecognizer.stop();
    isListening = false;
    if (micBtn) micBtn.classList.remove('listening');
    return;
  }

  try {
    speechRecognizer = new SpeechRec();
    speechRecognizer.lang = 'es-ES';
    speechRecognizer.interimResults = true;
    speechRecognizer.continuous = false;

    speechRecognizer.onstart = () => {
      isListening = true;
      if (micBtn) micBtn.classList.add('listening');
    };

    speechRecognizer.onresult = (event) => {
      let text = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        text += event.results[i][0].transcript;
      }
      const input = document.getElementById('gemini-prompt-input');
      if (input && text) input.value = text;
    };

    speechRecognizer.onerror = (e) => {
      console.warn('Speech recognition error:', e);
      isListening = false;
      if (micBtn) micBtn.classList.remove('listening');
    };

    speechRecognizer.onend = () => {
      isListening = false;
      if (micBtn) micBtn.classList.remove('listening');
    };

    speechRecognizer.start();
  } catch (err) {
    console.error(err);
    isListening = false;
    if (micBtn) micBtn.classList.remove('listening');
  }
}

// Síntesis de Voz (Text-to-Speech)
function speakText(text) {
  if (!('speechSynthesis' in window)) {
    alert('Síntesis de voz no disponible.');
    return;
  }
  window.speechSynthesis.cancel();
  const clean = text.replace(/🔊/g, '').replace(/<[^>]*>?/gm, '').replace(/```[\s\S]*?```/g, 'bloque de código omitido');
  const utter = new SpeechSynthesisUtterance(clean);
  utter.lang = 'es-ES';
  utter.rate = 1.05;
  window.speechSynthesis.speak(utter);
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
      item.style.padding = '10px 8px';
      item.style.borderBottom = '1px solid var(--border-subtle)';
      item.style.fontSize = 'var(--code-font-size)';
      item.style.fontFamily = 'var(--font-mono)';
      item.style.display = 'flex';
      item.style.justifyContent = 'space-between';
      item.style.alignItems = 'center';
      item.style.cursor = 'pointer';
      item.onclick = () => viewFileInRam(repoName, f.path);
      item.innerHTML = `
        <span style="color:var(--accent-cyan); display:flex; align-items:center; gap:6px;">📄 ${f.path}</span>
        <span style="color:var(--text-dim); font-size:0.75rem;">${f.size_bytes}B</span>
      `;
      listEl.appendChild(item);
    });
  } catch (e) {
    document.getElementById('tree-files-list').innerHTML = `<div style="color:var(--danger)">Error: ${e.message}</div>`;
  }
}

let currentModalFile = { repoName: null, filePath: null };
let rawFileContentCache = '';

function switchModalMode(mode) {
  const tabView = document.getElementById('modal-tab-view');
  const tabEdit = document.getElementById('modal-tab-edit');
  const preEl = document.getElementById('modal-file-content');
  const editorEl = document.getElementById('modal-file-editor');
  const commitControls = document.getElementById('modal-commit-controls');

  if (mode === 'edit') {
    if (tabView) tabView.classList.remove('active');
    if (tabEdit) tabEdit.classList.add('active');
    if (preEl) preEl.style.display = 'none';
    if (editorEl) {
      editorEl.style.display = 'block';
      editorEl.value = rawFileContentCache;
    }
    if (commitControls) commitControls.style.display = 'block';
  } else {
    if (tabEdit) tabEdit.classList.remove('active');
    if (tabView) tabView.classList.add('active');
    if (editorEl) editorEl.style.display = 'none';
    if (preEl) preEl.style.display = 'block';
    if (commitControls) commitControls.style.display = 'none';
  }
}

async function viewFileInRam(repoName, filePath) {
  currentModalFile = { repoName, filePath };
  switchModalMode('view');
  const modal = document.getElementById('file-viewer-modal');
  const title = document.getElementById('modal-file-title');
  const meta = document.getElementById('modal-file-meta');
  const content = document.getElementById('modal-file-content');
  
  if (title) title.innerText = filePath;
  if (meta) meta.innerText = 'Leyendo en RAM desde GitHub...';
  if (content) content.innerText = 'Cargando contenido sin descargar...';
  if (modal) modal.style.display = 'flex';

  try {
    const res = await GitHubEngine.readFile(repoName, filePath, 1, 300);
    rawFileContentCache = res.raw_text || res.content || '';
    if (meta) meta.innerText = `${res.showing_lines} de ${res.total_lines} líneas (${repoName})`;
    if (content) content.innerHTML = escapeHTML(res.content);
  } catch (e) {
    rawFileContentCache = '';
    if (meta) meta.innerText = 'Error';
    if (content) content.innerHTML = `<span style="color:var(--danger)">Error al leer archivo: ${escapeHTML(e.message)}</span>`;
  }
}

async function commitModalFileToGitHub() {
  if (!currentModalFile.repoName || !currentModalFile.filePath) return;
  const editorEl = document.getElementById('modal-file-editor');
  const msgInput = document.getElementById('modal-commit-msg');
  const newContent = editorEl.value;
  const message = msgInput.value.trim() || `update: ${currentModalFile.filePath} via Antigravity Mobile Hub`;

  const confirmed = confirm(`¿Confirmas crear un nuevo commit en '${currentModalFile.repoName}' para el archivo '${currentModalFile.filePath}' directamente desde la memoria RAM?`);
  if (!confirmed) return;

  const meta = document.getElementById('modal-file-meta');
  if (meta) meta.innerText = 'Enviando commit a GitHub...';

  try {
    const url = GitHubEngine.getApiUrl(`/api/commit?token=${encodeURIComponent(BridgeClient.token)}`);
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo: currentModalFile.repoName,
        path: currentModalFile.filePath,
        content: newContent,
        message: message
      })
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      rawFileContentCache = newContent;
      alert(`✅ Commit creado con éxito en GitHub!\nSHA: ${data.commit_sha ? data.commit_sha.substring(0, 7) : 'OK'}`);
      if (meta) meta.innerText = `Commit guardado (${data.commit_sha ? data.commit_sha.substring(0, 7) : 'OK'})`;
      switchModalMode('view');
      document.getElementById('modal-file-content').innerHTML = escapeHTML(newContent);
    } else {
      alert(`❌ Error al crear commit: ${data.error || 'Fallo desconocido'}`);
      if (meta) meta.innerText = 'Error al commitear';
    }
  } catch (e) {
    alert(`❌ Error de conexión al crear commit: ${e.message}`);
    if (meta) meta.innerText = 'Error';
  }
}

function closeFileViewer() {
  const modal = document.getElementById('file-viewer-modal');
  if (modal) modal.style.display = 'none';
  switchModalMode('view');
}

function analyzeCurrentModalFile() {
  closeFileViewer();
  if (currentModalFile.repoName && currentModalFile.filePath) {
    sendCodeToGemini(currentModalFile.repoName, currentModalFile.filePath);
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

function copyTerminalOutput() {
  const stream = document.getElementById('term-stream');
  if (stream && stream.textContent) {
    navigator.clipboard.writeText(stream.textContent).then(() => {
      alert('Registro de terminal copiado.');
    }).catch(() => {
      alert('No se pudo copiar.');
    });
  }
}

// ==============================================================================
// Manejo de Telemetría PC en Vivo (Hardware Monitoring)
// ==============================================================================

async function fetchTelemetry() {
  try {
    const url = GitHubEngine.getApiUrl(`/api/telemetry?token=${encodeURIComponent(BridgeClient.token)}`);
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      updateTelemetryUI(data);
    }
  } catch (e) {}
}

function updateTelemetryUI(data) {
  const bar = document.getElementById('telemetry-bar');
  if (bar) bar.style.display = 'flex';

  const cpuEl = document.getElementById('telem-cpu');
  const ramEl = document.getElementById('telem-ram');
  const pwrEl = document.getElementById('telem-pwr');

  if (cpuEl && data.cpu_percent !== undefined) {
    cpuEl.innerText = `💻 CPU: ${data.cpu_percent}%`;
    cpuEl.classList.toggle('alert', data.cpu_percent > 85);
  }
  if (ramEl && data.ram_used_gb !== undefined) {
    ramEl.innerText = `🧠 RAM: ${data.ram_used_gb}/${data.ram_total_gb}GB (${data.ram_percent}%)`;
    ramEl.classList.toggle('alert', data.ram_percent > 90);
  }
  if (pwrEl && data.ac_connected !== undefined) {
    pwrEl.innerText = `⚡ AC: ${data.ac_connected ? 'Conectado' : data.battery_percent + '%'}`;
  }
}

let telemetryTimer = null;
function startTelemetryLoop() {
  if (telemetryTimer) clearInterval(telemetryTimer);
  fetchTelemetry();
  telemetryTimer = setInterval(fetchTelemetry, 5000);
}

// ==============================================================================
// Manejo de Eventos del Puente (WebSocket Streaming)
// ==============================================================================

// Variables de Streaming en Vivo (Zero-Lag)
let currentStreamingBubble = null;
let currentStreamingText = '';

function appendChatChunk(chunk) {
  const scrollArea = document.getElementById('chat-scroll');
  if (!currentStreamingBubble) {
    currentStreamingBubble = document.createElement('div');
    currentStreamingBubble.className = 'message-card gemini';
    currentStreamingBubble.id = 'streaming-response-bubble';
    scrollArea.appendChild(currentStreamingBubble);
    currentStreamingText = '';
  }
  currentStreamingText += chunk;
  const safeText = escapeHTML(currentStreamingText).replace(/\n/g, '<br>');
  currentStreamingBubble.innerHTML = safeText + '<span style="opacity:0.8; animation:pulse-mic 1s infinite;"> ▌</span>';
  scrollArea.scrollTop = scrollArea.scrollHeight;
}

function finalizeChatChunk(fullText) {
  const finalText = fullText || currentStreamingText;
  if (currentStreamingBubble) {
    const safeText = escapeHTML(finalText).replace(/\n/g, '<br>');
    currentStreamingBubble.innerHTML = `${safeText} <button class="btn-speak" onclick="speakText(this.parentElement.innerText)" title="Escuchar respuesta">🔊</button>`;
    currentStreamingBubble.removeAttribute('id');
    currentStreamingBubble = null;
    currentStreamingText = '';
  } else if (finalText) {
    appendMessage('gemini', finalText);
  }
}

function handleBridgeEvents(data) {
  const hostBadge = document.getElementById('host-status-dot');
  const hostLabel = document.getElementById('host-status-label');

  if (data.event === 'bridge_connected') {
    if (hostBadge) hostBadge.classList.add('connected');
    if (hostLabel) hostLabel.innerText = 'Enlazado (PC)';
    startTelemetryLoop();
    if (typeof AuthManager !== 'undefined') AuthManager.checkSession();
  } else if (data.event === 'bridge_disconnected') {
    if (hostBadge) hostBadge.classList.remove('connected');
    if (hostLabel) hostLabel.innerText = 'Desconectado';
    if (telemetryTimer) clearInterval(telemetryTimer);
    const bar = document.getElementById('telemetry-bar');
    if (bar) bar.style.display = 'none';
  } else if (data.event === 'telemetry_update') {
    updateTelemetryUI(data.data);
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
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) bubble.remove();
    appendToolCall(data.tool, data.args);
  } else if (data.event === 'chat_chunk') {
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) bubble.remove();
    appendChatChunk(data.text);
  } else if (data.event === 'chat_response') {
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) bubble.remove();
    finalizeChatChunk(data.text);
  } else if (data.event === 'chat_error') {
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) bubble.remove();
    if (currentStreamingBubble) {
      currentStreamingBubble.remove();
      currentStreamingBubble = null;
    }
    appendMessage('gemini', `<span style="color:var(--danger)">[Error] ${data.message}</span>`);
  }
}

// ==============================================================================
// Módulo 4: Ajustes, Cuentas y Emparejamiento por Código
// ==============================================================================

function initSettingsInputs() {
  const hostInput = document.getElementById('input-bridge-host');
  if (hostInput) hostInput.value = BridgeClient.getHost();

  const modelSelect = document.getElementById('setting-gemini-model');
  if (modelSelect) {
    modelSelect.value = GeminiEngine.config.model;
  }

  if (typeof AuthManager !== 'undefined') {
    AuthManager.updateUI();
  }
}

function openPinModal() {
  const modal = document.getElementById('pin-modal');
  if (modal) {
    modal.style.display = 'flex';
    const input = document.getElementById('input-pin-code');
    if (input) {
      input.value = '';
      input.focus();
    }
  }
}

function closePinModal() {
  const modal = document.getElementById('pin-modal');
  if (modal) modal.style.display = 'none';
}

function autofillDefaultPin() {
  const input = document.getElementById('input-pin-code');
  if (input) input.value = '749215';
}

async function submitPinCode() {
  const input = document.getElementById('input-pin-code');
  const pin = input ? input.value.trim() : '';
  if (!pin) {
    alert('Por favor ingresa el PIN de 6 dígitos.');
    return;
  }
  const res = await AuthManager.pairWithPin(pin);
  if (res.success) {
    closePinModal();
    alert('✅ ' + res.message);
    BridgeClient.connect();
  } else {
    alert('❌ ' + res.message);
  }
}

async function syncSessionFromPC() {
  const banner = document.getElementById('conn-test-feedback');
  if (banner) {
    banner.style.display = 'block';
    banner.style.color = 'var(--accent-blue)';
    banner.innerText = '⏳ Sincronizando cuentas con PC...';
  }

  const res = await AuthManager.syncFromPC();
  if (res && res.success) {
    if (banner) {
      banner.style.color = 'var(--success)';
      banner.innerHTML = `✅ <b>Cuentas vinculadas:</b> ${res.email} y @${res.user}`;
    }
    loadReposList(res.user);
    BridgeClient.connect();
  } else {
    if (banner) {
      banner.style.color = 'var(--danger)';
      banner.innerHTML = `❌ No se pudo sincronizar automáticamente. Verifica que el Host PC esté activo.`;
    }
  }
}

function startGitHubDeviceFlow() {
  const modal = document.getElementById('device-code-modal');
  if (modal) modal.style.display = 'flex';
}

function closeDeviceCodeModal() {
  const modal = document.getElementById('device-code-modal');
  if (modal) modal.style.display = 'none';
}

function openGitHubDevicePage() {
  window.open('https://github.com/login/device', '_blank');
}

function changeGeminiModel(modelId) {
  GeminiEngine.config.model = modelId;
  GeminiEngine.saveConfig();
  updateModelPillLabel();
}

async function testHostConnection() {
  const banner = document.getElementById('conn-test-feedback');
  if (!banner) return;
  banner.style.display = 'block';
  banner.style.background = 'var(--bg-surface-elevated)';
  banner.style.color = 'var(--accent-blue)';
  banner.innerText = '⏳ Probando conexión con PC...';

  const host = document.getElementById('input-bridge-host').value.trim() || BridgeClient.getHost();
  const token = BridgeClient.token || 'antigravity-secret-key';

  try {
    const start = Date.now();
    const res = await fetch(`http://${host}/api/status?token=${encodeURIComponent(token)}`);
    const latency = Date.now() - start;
    if (res.ok) {
      const data = await res.json();
      banner.style.color = 'var(--success)';
      banner.innerHTML = `✅ <b>Enlace exitoso con PC:</b> ${data.hostname || host} (${latency}ms)`;
      localStorage.setItem('bridge_host', host);
      BridgeClient.connect();
      AuthManager.checkSession();
    } else {
      banner.style.color = 'var(--danger)';
      banner.innerHTML = `❌ Error de autenticación HTTP ${res.status}.`;
    }
  } catch (err) {
    banner.style.color = 'var(--danger)';
    banner.innerHTML = `❌ No se pudo conectar a ${host}: ${err.message}`;
  }
}

// ==============================================================================
// Módulo 5: Historial de Conversaciones (113 Sesiones Antigravity & Gemini Flash)
// ==============================================================================

let currentConvFilter = 'antigravity';
let cachedAgyConversations = [];
let cachedGeminiHistory = [];

async function loadConversationsList() {
  const container = document.getElementById('conv-list-container');
  if (!container) return;

  container.innerHTML = `
    <div style="text-align:center; padding:25px; color:var(--text-muted);">
      ⏳ Cargando conversaciones desde la PC...
    </div>
  `;

  if (currentConvFilter === 'antigravity') {
    try {
      const res = await fetch(BridgeClient.apiUrl('/api/antigravity/conversations'));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      cachedAgyConversations = data.conversations || [];
      renderAgyConversations(cachedAgyConversations);
    } catch (err) {
      container.innerHTML = `
        <div style="text-align:center; padding:25px; color:var(--danger);">
          ❌ Error al conectar con el servidor: ${escapeHTML(err.message)}<br>
          <button class="btn-action-small" style="margin-top:10px;" onclick="loadConversationsList()">Reintentar</button>
        </div>
      `;
    }
  } else {
    try {
      const res = await fetch(BridgeClient.apiUrl('/api/gemini/history'));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      cachedGeminiHistory = data.history || [];
      renderGeminiHistory(cachedGeminiHistory);
    } catch (err) {
      container.innerHTML = `
        <div style="text-align:center; padding:25px; color:var(--danger);">
          ❌ Error al cargar historial de Gemini: ${escapeHTML(err.message)}
        </div>
      `;
    }
  }
}

function switchConvFilter(type) {
  currentConvFilter = type;
  const btnAgy = document.getElementById('btn-filter-agy');
  const btnGemini = document.getElementById('btn-filter-gemini');

  if (type === 'antigravity') {
    if (btnAgy) {
      btnAgy.style.background = 'var(--accent-indigo)';
      btnAgy.style.fontWeight = '700';
    }
    if (btnGemini) {
      btnGemini.style.background = 'var(--bg-surface-elevated)';
      btnGemini.style.fontWeight = 'normal';
    }
  } else {
    if (btnAgy) {
      btnAgy.style.background = 'var(--bg-surface-elevated)';
      btnAgy.style.fontWeight = 'normal';
    }
    if (btnGemini) {
      btnGemini.style.background = 'var(--accent-indigo)';
      btnGemini.style.fontWeight = '700';
    }
  }

  loadConversationsList();
}

function filterConversationsUI(query) {
  const q = (query || '').toLowerCase().trim();
  if (currentConvFilter === 'antigravity') {
    if (!q) {
      renderAgyConversations(cachedAgyConversations);
      return;
    }
    const filtered = cachedAgyConversations.filter(c => 
      (c.title && c.title.toLowerCase().includes(q)) ||
      (c.summary && c.summary.toLowerCase().includes(q)) ||
      (c.conversation_id && c.conversation_id.toLowerCase().includes(q))
    );
    renderAgyConversations(filtered);
  } else {
    if (!q) {
      renderGeminiHistory(cachedGeminiHistory);
      return;
    }
    const filtered = cachedGeminiHistory.filter(h =>
      (h.prompt && h.prompt.toLowerCase().includes(q)) ||
      (h.response && h.response.toLowerCase().includes(q))
    );
    renderGeminiHistory(filtered);
  }
}

function renderAgyConversations(list) {
  const container = document.getElementById('conv-list-container');
  if (!container) return;

  if (!list || list.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:25px; color:var(--text-muted);">
        No se encontraron conversaciones.
      </div>
    `;
    return;
  }

  let html = '';
  list.forEach(conv => {
    const title = escapeHTML(conv.title || 'Conversación sin título');
    const summary = escapeHTML(conv.summary || 'Sin resumen disponible');
    const dateStr = conv.timestamp ? new Date(conv.timestamp).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' }) : '';
    const safeId = escapeHTML(conv.conversation_id || '');

    html += `
      <div class="conv-card" onclick="openConversationDetail('${safeId}', 'antigravity', '${title.replace(/'/g, "\\'")}', '${dateStr}')">
        <div class="conv-title" style="display:flex; justify-content:space-between; align-items:flex-start;">
          <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">💬 ${title}</span>
          <span style="font-size:0.7rem; color:var(--text-muted); margin-left:8px; flex-shrink:0;">${dateStr}</span>
        </div>
        <div class="conv-preview" style="display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.3; margin-top:3px;">
          ${summary}
        </div>
        <div style="font-size:0.68rem; color:var(--accent-cyan); margin-top:5px; font-family:var(--font-mono);">
          ID: ${safeId.substring(0, 8)}...
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderGeminiHistory(list) {
  const container = document.getElementById('conv-list-container');
  if (!container) return;

  if (!list || list.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:25px; color:var(--text-muted);">
        No hay consultas recientes en el historial de Gemini.
      </div>
    `;
    return;
  }

  let html = '';
  list.forEach((item, idx) => {
    const prompt = escapeHTML(item.prompt || '');
    const respPreview = escapeHTML((item.response || '').substring(0, 160));
    const model = escapeHTML(item.model || 'gemini-3.8-flash');
    const timeStr = item.timestamp ? new Date(item.timestamp * 1000).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' }) : '';

    html += `
      <div class="conv-card" onclick="openGeminiDetail(${idx})">
        <div class="conv-title" style="display:flex; justify-content:space-between; align-items:center;">
          <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">⚡ ${prompt}</span>
          <span class="badge-tag" style="font-size:0.65rem; margin-left:6px;">${model}</span>
        </div>
        <div class="conv-preview" style="display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.3; margin-top:3px;">
          ${respPreview}...
        </div>
        <div style="font-size:0.7rem; color:var(--text-muted); margin-top:4px;">${timeStr}</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

async function openConversationDetail(cid, type, title, meta) {
  const modal = document.getElementById('conv-reader-modal');
  const titleEl = document.getElementById('conv-reader-title');
  const metaEl = document.getElementById('conv-reader-meta');
  const msgContainer = document.getElementById('conv-reader-messages');

  if (!modal || !msgContainer) return;

  if (titleEl) titleEl.innerText = title;
  if (metaEl) metaEl.innerText = `${meta} • ID: ${cid}`;
  msgContainer.innerHTML = `
    <div style="text-align:center; padding:20px; color:var(--text-muted);">
      ⏳ Cargando mensajes de la conversación...
    </div>
  `;
  modal.style.display = 'flex';

  try {
    const res = await fetch(BridgeClient.apiUrl(`/api/antigravity/conversation?id=${encodeURIComponent(cid)}`));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const messages = data.messages || [];

    if (messages.length === 0) {
      msgContainer.innerHTML = `
        <div style="text-align:center; padding:20px; color:var(--text-muted);">
          No se encontraron mensajes registrados en esta sesión.
        </div>
      `;
      return;
    }

    let html = '';
    messages.forEach(msg => {
      const isUser = msg.role === 'user';
      const roleName = isUser ? '👤 Tú' : (msg.role === 'assistant' ? '⚡ Antigravity' : '⚙️ Sistema');
      const cardClass = isUser ? 'user' : (msg.role === 'assistant' ? 'gemini' : 'system');
      const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) : '';
      const text = formatMessageText(msg.content || '');

      html += `
        <div class="message-card ${cardClass}" style="margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.72rem; opacity:0.8;">
            <b>${roleName}</b>
            <span>${time}</span>
          </div>
          <div style="font-size:0.85rem; line-height:1.45; word-break:break-word;">
            ${text}
          </div>
        </div>
      `;
    });

    msgContainer.innerHTML = html;
    msgContainer.scrollTop = 0;
  } catch (err) {
    msgContainer.innerHTML = `
      <div style="text-align:center; padding:20px; color:var(--danger);">
        ❌ Error al cargar transcripción: ${escapeHTML(err.message)}
      </div>
    `;
  }
}

function openGeminiDetail(idx) {
  const item = cachedGeminiHistory[idx];
  if (!item) return;

  const modal = document.getElementById('conv-reader-modal');
  const titleEl = document.getElementById('conv-reader-title');
  const metaEl = document.getElementById('conv-reader-meta');
  const msgContainer = document.getElementById('conv-reader-messages');

  if (!modal || !msgContainer) return;

  if (titleEl) titleEl.innerText = item.prompt || 'Consulta Gemini';
  if (metaEl) metaEl.innerText = `${item.model || 'gemini-3.8-flash'} • ${item.timestamp ? new Date(item.timestamp * 1000).toLocaleString('es-ES') : ''}`;

  let html = `
    <div class="message-card user" style="margin-bottom:10px;">
      <div style="font-size:0.72rem; opacity:0.8; margin-bottom:4px;"><b>👤 Consulta:</b></div>
      <div style="font-size:0.85rem; line-height:1.45;">${escapeHTML(item.prompt || '')}</div>
    </div>
  `;

  if (item.thinking) {
    html += `
      <div class="message-card" style="margin-bottom:10px; background:#12141a; border-left:3px solid var(--accent-indigo);">
        <div style="font-size:0.72rem; color:var(--accent-indigo); margin-bottom:4px;"><b>🧠 Razonamiento (Thinking Budget):</b></div>
        <div style="font-size:0.78rem; font-family:var(--font-mono); color:var(--text-muted); white-space:pre-wrap;">${escapeHTML(item.thinking)}</div>
      </div>
    `;
  }

  html += `
    <div class="message-card gemini" style="margin-bottom:10px;">
      <div style="font-size:0.72rem; opacity:0.8; margin-bottom:4px;"><b>⚡ Gemini 3.8 Flash High:</b></div>
      <div style="font-size:0.85rem; line-height:1.45;">${formatMessageText(item.response || '')}</div>
    </div>
  `;

  msgContainer.innerHTML = html;
  modal.style.display = 'flex';
  msgContainer.scrollTop = 0;
}

function closeConvReader() {
  const modal = document.getElementById('conv-reader-modal');
  if (modal) modal.style.display = 'none';
}

function formatMessageText(content) {
  if (!content) return '';
  let text = escapeHTML(content);
  // Bloques de código
  text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (m, lang, code) => {
    return `<pre style="background:#0c0d12; padding:8px 10px; border-radius:6px; overflow-x:auto; font-family:var(--font-mono); font-size:0.8rem; margin:6px 0; border:1px solid var(--border-subtle); color:#a7f3d0;"><code>${code}</code></pre>`;
  });
  // Código inline
  text = text.replace(/`([^`]+)`/g, '<code style="background:#161922; padding:2px 5px; border-radius:4px; font-family:var(--font-mono); font-size:0.82rem; color:var(--accent-cyan);">$1</code>');
  // Negrita
  text = text.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  // Saltos de línea
  text = text.replace(/\n/g, '<br>');
  return text;
}

// ==============================================================================
// Módulo 6: Proyectos de Desarrollo en PC (46 Proyectos en Windows)
// ==============================================================================

let cachedProjects = [];

async function loadProjectsList() {
  const container = document.getElementById('projects-list-container');
  if (!container) return;

  container.innerHTML = `
    <div style="text-align:center; padding:25px; color:var(--text-muted);">
      ⏳ Escaneando proyectos locales en la PC...
    </div>
  `;

  try {
    const res = await fetch(BridgeClient.apiUrl('/api/projects'));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cachedProjects = data.projects || [];

    if (cachedProjects.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:25px; color:var(--text-muted);">
          No se encontraron carpetas de proyectos en las rutas monitoreadas.
        </div>
      `;
      return;
    }

    let html = '';
    cachedProjects.forEach(proj => {
      const name = escapeHTML(proj.name || 'Proyecto');
      const path = escapeHTML(proj.path || '');
      const isGit = proj.is_git;
      const branch = escapeHTML(proj.branch || 'no-git');
      const commit = escapeHTML((proj.commit || '').substring(0, 7));
      const status = proj.status || 'clean';
      const statusBadge = isGit 
        ? (status === 'modified' ? '<span class="badge-tag" style="background:#b45309;">⚠️ Modificado</span>' : '<span class="badge-tag" style="background:#065f46;">✓ Limpio</span>')
        : '<span class="badge-tag" style="background:#374151;">📁 Directorio</span>';

      html += `
        <div class="project-card">
          <div class="project-title" style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:0.95rem; font-weight:700; color:#fff;">📦 ${name}</span>
            <div>${statusBadge}</div>
          </div>
          <div style="font-size:0.72rem; color:var(--accent-cyan); font-family:var(--font-mono); word-break:break-all; margin:3px 0 6px 0;">
            ${path}
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
            <div style="font-size:0.72rem; color:var(--text-muted);">
              ${isGit ? `🌿 Rama: <b>${branch}</b> • #${commit}` : 'Directorio local'}
            </div>
            <button class="btn-action-small" style="background:var(--accent-indigo); font-weight:600;" onclick="switchProject('${path.replace(/\\/g, '\\\\')}')">
              👉 Activar en PC
            </button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `
      <div style="text-align:center; padding:25px; color:var(--danger);">
        ❌ Error al conectar con el servidor: ${escapeHTML(err.message)}<br>
        <button class="btn-action-small" style="margin-top:10px;" onclick="loadProjectsList()">Reintentar</button>
      </div>
    `;
  }
}

async function switchProject(targetPath) {
  try {
    const res = await fetch(BridgeClient.apiUrl('/api/projects/switch'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: targetPath })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    alert(`✅ Proyecto activo cambiado a:\n${data.name} (${data.path})`);
    loadProjectsList();
  } catch (err) {
    alert(`❌ No se pudo cambiar de proyecto: ${err.message}`);
  }
}
