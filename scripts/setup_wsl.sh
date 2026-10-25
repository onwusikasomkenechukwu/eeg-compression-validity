#!/usr/bin/env bash
# Builds the project's Python environment on Linux (WSL2, a workstation, or the cluster)
# and runs the test suite.
# Usage: bash scripts/setup_wsl.sh   -> environment at ~/venvs/eegcv
#        TORCH_INDEX=<CUDA wheel index URL from pytorch.org for your driver> bash scripts/setup_wsl.sh   (NVIDIA)
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv --version

VENV="$HOME/venvs/eegcv"
mkdir -p "$(dirname "$VENV")"
[ -x "$VENV/bin/python" ] || uv venv --python 3.12 "$VENV"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# CPU build by default; on an NVIDIA machine set TORCH_INDEX to the CUDA wheel index from pytorch.org.
uv pip install --python "$VENV/bin/python" torch==2.14.1 \
    --index-url "${TORCH_INDEX:-https://download.pytorch.org/whl/cpu}"
uv pip install --python "$VENV/bin/python" -r "$ROOT/requirements.txt"

"$VENV/bin/python" -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
"$VENV/bin/python" -m pytest "$ROOT/tests" -q -p no:cacheprovider
