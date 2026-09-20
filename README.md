# ⚡ Antigravity Mobile Hub — Versión Suprema v2.1.0

[![Android Build](https://github.com/zero-phoenix/Antigravity-Mobile-Hub/actions/workflows/release_apk.yml/badge.svg)](https://github.com/zero-phoenix/Antigravity-Mobile-Hub/actions/workflows/release_apk.yml)
[![GitHub Release](https://img.shields.io/github/v/release/zero-phoenix/Antigravity-Mobile-Hub?color=blue&label=Release)](https://github.com/zero-phoenix/Antigravity-Mobile-Hub/releases)
[![Android Compatibility](https://img.shields.io/badge/Android-7.0%2B%20(API%2024--36)-green)](https://github.com/zero-phoenix/Antigravity-Mobile-Hub)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Antigravity Mobile Hub (Versión Suprema v2.1.0)** es una suite de ingeniería agéntica y desarrollo móvil para Android con interfaz Cyber-OLED ultrarrápida:
1. **Autenticación por Código Móvil (Cero API Keys Manuales)**: Vinculación transparente mediante **PIN de Emparejamiento de 6 dígitos** y **GitHub Device Code Flow**. Hereda automáticamente la sesión de Google (`david.chavez.nge@gmail.com`) y GitHub (`@zero-phoenix`).
2. **Google Gemini 2.0 Flash Oficial con Streaming**: Inferencia ultra veloz token por token (<400ms de latencia) mediante `gemini-2.0-flash` y `gemini-2.0-flash-lite`.
3. **GitHub Cloud Zero-Download + In-Memory Commits**: Lee código, explora árboles completos y **crea o edita commits en GitHub directamente en RAM** sin clonar ni gastar almacenamiento del teléfono.
4. **Telemetría PC en Vivo**: Monitor en tiempo real de uso de CPU, RAM y energía en Windows vía ctypes ultrarrápido sin librerías externas.
5. **PowerShell en Vivo y Dictado por Voz**: Terminal remota interactiva en tiempo real y comandos por micrófono.

---

## 📲 Descarga e Instalación en Android

El producto principal es el binario compilado listo para instalar:

1. Ve a la sección de **[Releases](https://github.com/zero-phoenix/Antigravity-Mobile-Hub/releases)** de este repositorio.
2. Descarga el archivo **`Antigravity-Mobile-Hub-v2.1.0.apk`** en tu celular.
3. Abre el archivo descargado en tu teléfono y pulsa **Instalar**.
4. ¡Listo! La app se instalará con su propio icono en el launcher de Android y se ejecutará a pantalla completa sin barras de navegador.

> **Modo PWA Alternativo**: También puedes acceder directamente desde Google Chrome a `http://<IP_DE_TU_PC>:8765/` y presionar *"Agregar a la pantalla principal"*.

---

## 🚀 Módulos y Funcionalidades

```
┌─────────────────────────────────────────────────────────────┐
│                 ⚡ ANTIGRAVITY MOBILE HUB                   │
├──────────────┬──────────────┬───────────────┬───────────────┤
│   💬 GEMINI  │   ☁️ REPOS   │  💻 TERMINAL  │   ⚙️ AJUSTES  │
└──────────────┴──────────────┴───────────────┴───────────────┘
```

### 1. 💬 Gemini Intelligence Workspace
- **Familia Oficial Gemini 2.0**: Predeterminado a `⚡ Gemini 2.0 Flash` (baja latencia y respuestas instantáneas), con opciones para `Gemini 2.0 Flash Lite`, `Gemini 1.5 Flash` y `Gemini 1.5 Pro`.
- **Streaming Token a Token**: Las palabras aparecen inmediatamente en pantalla a medida que se generan, eliminando tiempos de espera.
- **Thinking Budget**: Controla el esfuerzo de razonamiento interno:
  - `⚡ Rápido (0)`: Inferencia inmediata.
  - `🧠 Analítico (2k)`: Cadena de razonamiento de 2048 tokens.
  - `🔬 Deep Research (8k)`: Auditoría y depuración exhaustiva de código.
- **🛡️ Grounding Estricto**: Prohíbe inventar APIs o código no respaldado por los repositorios; exige citas directas de archivo y línea.

### 2. ☁️ Explorador Cloud Universal (Zero-Download)
- **Cero uso de almacenamiento**: Explora archivos y código fuente directamente en memoria RAM. No se descargan gigabytes de historial `git`.
- **Repositorios Propios y de Terceros**:
  - Acceso a tus 10 repositorios privados (`meta-orquesta`, `yabausevita`, `Magisys`, `jkvita`, etc.).
  - Barra de búsqueda universal: Escribe cualquier identificador o pega cualquier URL (ej: `vitasdk/vita-headers` o `https://github.com/owner/repo`).
- **Caché LRU en RAM**: Mantiene árboles y archivos en memoria durante 5 minutos para navegación instantánea en milisegundos.
- **Botón "Consultar a Gemini"**: Transfiere automáticamente cualquier archivo remoto al contexto del modelo para análisis de bugs o arquitectura.

### 3. 💻 Terminal Remota y Delegación a PC
- **PowerShell en Vivo**: Ejecuta comandos en tu computadora Windows (`git status`, compilaciones de VitaSDK, scripts de `docgen.py`) con streaming de salida en tiempo real.
- **Cadena de Mando**: Gemini puede invocar `delegate_to_desktop` para ejecutar tareas de edición, git o testing en Windows de forma autónoma y reportarte el resultado al teléfono.

### 4. ⚙️ Ajustes de Interfaz y Tipografía
- **Escala de Texto General**: 4 niveles ajustables (*Compacto 0.85x*, *Estándar 1.0x*, *Grande 1.15x*, *Extra 1.30x*).
- **Escala de Terminal y Código**: 3 niveles (*Pequeño 0.85x*, *Normal 1.0x*, *Grande 1.20x*).
- **Tema Cyber-Dark OLED**: Paleta `#08090b` que ahorra batería en pantallas OLED y evita fatiga visual.

---

## 🛡️ Auditoría Popperiana de Robustez

El código ha sido sometido a una batería de falsacionismo de Popper para garantizar la ausencia de fallos:

| Hipótesis Falsada | Prueba Ejecutada | Resultado |
|---|---|---|
| **Inyección XSS** | Inyección de código malicioso en código remoto de GitHub | **Superada**: Sanitización obligatoria con `escapeHTML()` en chat y visor. |
| **Bloqueo Cleartext** | Conexión HTTP a IP local en Android 9+ | **Superada**: `usesCleartextTraffic="true"` en `AndroidManifest.xml`. |
| **Arranque Offline** | Apertura de la app sin conexión a internet | **Superada**: Assets embebidos en el APK (`file:///android_asset/`). |
| **Resiliencia de URLs** | Fuzzing de URLs malformadas y repositorios inexistentes | **Superada**: Captura de errores con mensajes claros y fallback seguro. |
| **Compilación CI/CD** | Build desatendido en GitHub Actions | **Superada**: Gradle 8.2 + JDK 17 con firma debug universal. |

---

## 💻 Inicio del Servidor Puente en la PC

Para habilitar el control remoto y el streaming de terminal desde tu celular:

```powershell
# Iniciar servidor Gateway en Windows
.\bridge\launch_bridge.ps1
```

Abre la dirección IP local mostrada (ej. `http://192.168.1.XX:8765/?token=antigravity-secret-key`) en la app instalada en tu Android.

---

## 📄 Licencia

Este proyecto está licenciado bajo los términos de la Licencia MIT.
