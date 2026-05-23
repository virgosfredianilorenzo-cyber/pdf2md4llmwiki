#!/bin/bash
# ============================================================
# start.sh — PDF2LLMWiki · Linux
# Usage : bash start.sh
# ============================================================

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
err()  { echo -e "${RED}✗${NC}  $1"; exit 1; }
step() { echo -e "\n${CYAN}▸${NC} $1"; }

echo ""
echo "  ╔══════════════════════════════╗"
echo "  ║       PDF2LLMWiki            ║"
echo "  ║       Linux                  ║"
echo "  ╚══════════════════════════════╝"
echo ""

# ── 1. Python 3.10+ ─────────────────────────────────────────
step "Vérification Python"
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c "import sys; assert sys.version_info >= (3,10)" 2>/dev/null; then
            PYTHON="$cmd"
            ok "$cmd — $($cmd --version 2>&1)"
            break
        fi
    fi
done
[ -z "$PYTHON" ] && err "Python 3.10+ requis.\n  Ubuntu/Debian : sudo apt install python3.11"

# ── 2. Venv ─────────────────────────────────────────────────
step "Environnement virtuel"
if [ ! -d ".venv" ]; then
    $PYTHON -m venv .venv && ok "venv créé dans .venv/"
else
    ok "venv existant"
fi
source .venv/bin/activate

# ── 3. Dépendances Python ───────────────────────────────────
step "Dépendances Python"
if ! python -c "import fastapi" 2>/dev/null; then
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    ok "dépendances installées"
else
    ok "dépendances déjà présentes"
fi

# ── 4. Ollama ───────────────────────────────────────────────
step "Ollama"
if ! command -v ollama &>/dev/null; then
    warn "Ollama absent — installation en cours..."
    _tmp_install=$(mktemp /tmp/ollama_install.XXXXXX.sh)
    curl -fsSL https://ollama.com/install.sh -o "$_tmp_install"
    sh "$_tmp_install"
    rm -f "$_tmp_install"
fi
ok "Ollama $(ollama --version 2>/dev/null | head -1)"

# ── 5. Daemon Ollama ────────────────────────────────────────
step "Daemon Ollama"
if ! curl -sf http://localhost:11434 &>/dev/null; then
    ollama serve >> /tmp/pdf2llmwiki_ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "  démarrage (pid $OLLAMA_PID)..."
    for i in $(seq 1 15); do
        sleep 1
        curl -sf http://localhost:11434 &>/dev/null && break
        [ "$i" -eq 15 ] && err "Ollama ne répond pas après 15s.\n  Log : /tmp/pdf2llmwiki_ollama.log"
    done
    ok "daemon actif (pid $OLLAMA_PID)"
else
    ok "daemon déjà actif"
fi

# ── 6. Modèle LLM ───────────────────────────────────────────
step "Modèle LLM"
MODEL=$(python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['model'])" 2>/dev/null || echo "qwen2.5:7b")
MODEL_BASE="${MODEL%%:*}"
if ollama list 2>/dev/null | grep -q "^${MODEL_BASE}"; then
    ok "modèle $MODEL présent"
else
    warn "Modèle $MODEL absent — téléchargement (peut prendre plusieurs minutes)..."
    ollama pull "$MODEL" || err "Échec du téléchargement.\n  Vérifie ta connexion internet (nécessaire une seule fois)."
    ok "modèle $MODEL prêt"
fi

# ── 7. Dossier output ───────────────────────────────────────
mkdir -p output
ok "dossier output/ prêt"

# ── 8. Port ─────────────────────────────────────────────────
PORT=$(python -c "import yaml; print(yaml.safe_load(open('config.yaml')).get('port', 8000))" 2>/dev/null || echo "8000")

if command -v lsof &>/dev/null && lsof -i ":$PORT" &>/dev/null 2>&1; then
    PORT=$((PORT+1))
    warn "Port occupé — bascule sur $PORT"
fi

echo ""
echo "  ┌──────────────────────────────────────────┐"
echo "  │  ✓ Tout est prêt                         │"
echo "  │  → http://localhost:${PORT}                  │"
echo "  │  Ctrl+C pour arrêter                     │"
echo "  └──────────────────────────────────────────┘"
echo ""

# Ouvre le navigateur après 1.5s (best-effort)
(sleep 1.5 && {
    command -v xdg-open &>/dev/null && xdg-open "http://localhost:$PORT" && exit
    true
}) &

PORT=$PORT python app.py
