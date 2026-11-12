# Carregar com: source ./env.sh (bash ou zsh).
if [ -n "${ZSH_VERSION:-}" ]; then
    _FLOW_ENV_SOURCE="${(%):-%x}"
else
    _FLOW_ENV_SOURCE="${BASH_SOURCE[0]}"
fi
export FLOW_SYSTEM_DIR="$(cd -- "$(dirname -- "$_FLOW_ENV_SOURCE")" && pwd)"
export SISTEMA_CRIATIVOS_DIR="$FLOW_SYSTEM_DIR"
export PATH="$FLOW_SYSTEM_DIR:$FLOW_SYSTEM_DIR/.venv/bin:/opt/homebrew/opt/ffmpeg-full/bin:$HOME/.local/bin:/opt/homebrew/bin:$PATH"
export FFMPEG="/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
export WHISPER_MODEL="$HOME/whisper/ggml-small.bin"
export RVM_DIR="$HOME/tools/rvm"
export PYTHONDONTWRITEBYTECODE=1
export FLOW_LOCK="${FLOW_LOCK:-$FLOW_SYSTEM_DIR/.flow_lane.lock}"
unset _FLOW_ENV_SOURCE
