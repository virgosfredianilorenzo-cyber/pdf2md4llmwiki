#!/bin/bash
# ============================================================
# install_ollama.sh — Installation Ollama + modèle LLM local
# Compatible Linux (Ubuntu/Debian) et macOS
# ============================================================

set -e

echo "======================================"
echo "  PDF2LLMWiki — Installation Ollama"
echo "======================================"

OS="$(uname -s)"

# --- Installation Ollama ---
if command -v ollama &>/dev/null; then
    echo "✓ Ollama déjà installé : $(ollama --version)"
else
    echo "→ Installation de Ollama..."
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install ollama
        else
            echo "Télécharge Ollama sur https://ollama.com/download/mac"
            open "https://ollama.com/download/mac" 2>/dev/null || true
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        _tmp_install=$(mktemp /tmp/ollama_install.XXXXXX.sh)
        curl -fsSL https://ollama.com/install.sh -o "$_tmp_install"
        sh "$_tmp_install"
        rm -f "$_tmp_install"
    else
        echo "Windows : télécharge https://ollama.com/download/windows"
        exit 1
    fi
fi

# --- Démarrage service Ollama ---
echo "→ Démarrage du service Ollama..."
if [ "$OS" = "Linux" ]; then
    systemctl is-active --quiet ollama 2>/dev/null || ollama serve &>/dev/null &
    sleep 2
fi

# --- Choix du modèle ---
echo ""
echo "Quel modèle veux-tu installer ?"
echo "  1) mistral:7b      (4 GB RAM — recommandé pour débuter)"
echo "  2) llama3.2:3b     (2 GB RAM — rapide, CPU suffisant)"
echo "  3) qwen2.5:7b      (4 GB RAM — excellent en français)"
echo "  4) mistral:7b-instruct-q4_K_M  (2.5 GB RAM — quantifié)"
echo ""
read -p "Choix [1-4, défaut=3] : " choice
choice=${choice:-3}

case $choice in
    1) MODEL="mistral:7b" ;;
    2) MODEL="llama3.2:3b" ;;
    3) MODEL="qwen2.5:7b" ;;
    4) MODEL="mistral:7b-instruct-q4_K_M" ;;
    *) MODEL="qwen2.5:7b" ;;
esac

echo "→ Téléchargement de $MODEL..."
ollama pull "$MODEL"

echo ""
echo "✓ Ollama installé avec $MODEL"
echo ""
echo "Écris le modèle dans config.yaml :"
echo "  model: $MODEL"
echo ""
echo "Lance ensuite : python -m pip install -r requirements.txt"
echo "Puis          : python app.py"
