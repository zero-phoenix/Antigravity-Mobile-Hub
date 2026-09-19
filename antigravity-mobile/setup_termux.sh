#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Script de instalación y configuración de Antigravity Mobile en Termux (Android)
# ==============================================================================

set -e

echo "=== [1/5] Actualizando paquetes base de Termux ==="
pkg update -y && pkg upgrade -y

echo "=== [2/5] Instalando herramientas esenciales ==="
pkg install -y python git nodejs openssh termux-api clang make libffi

echo "=== [3/5] Instalando dependencias de Python ==="
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pip install --upgrade pip
pip install -r "$DIR/requirements.txt"

echo "=== [4/5] Creando alias global 'antigravity' en ~/.bashrc ==="
BASHRC="$HOME/.bashrc"
ALIAS_CMD="alias antigravity=\"python $DIR/main.py\""

if ! grep -q "alias antigravity=" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Antigravity Mobile CLI" >> "$BASHRC"
    echo "$ALIAS_CMD" >> "$BASHRC"
    echo "Alias añadido a ~/.bashrc."
fi

echo "=== [5/5] Verificando integración con hardware Termux:API ==="
if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --title "Antigravity Mobile" --content "¡Instalación completada con éxito en tu teléfono!"
    echo "[✓] Notificación de bienvenida enviada a la barra de estado de Android."
else
    echo "[!] termux-api (paquete Termux o APK) no detectado. Las notificaciones nativas estarán en modo simulado."
fi

echo ""
echo "=================================================================="
echo " ¡Antigravity Mobile ha sido instalado exitosamente en tu celular!"
echo " Para iniciar:"
echo " 1. Asegúrate de definir tu clave: export GEMINI_API_KEY='tu_clave'"
echo " 2. Ejecuta: antigravity"
echo "=================================================================="
