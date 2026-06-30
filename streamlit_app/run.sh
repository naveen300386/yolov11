#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$(dirname "$SCRIPT_DIR")/streamlit_venv"
PYTHON="$VENV_DIR/bin/python"
STREAMLIT="$VENV_DIR/bin/streamlit"

# Install packages if streamlit is missing
if [ ! -f "$STREAMLIT" ]; then
    echo "streamlit binary not found at $STREAMLIT, trying to install..."
    if command -v uv &> /dev/null; then
        uv pip install --python "$PYTHON" streamlit ultralytics opencv-python-headless Pillow sqlalchemy bcrypt plotly pandas python-dotenv authlib httpx streamlit-option-menu numpy requests
    else
        "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
    fi
fi

# If streamlit still not found, use python -m streamlit
if [ ! -f "$STREAMLIT" ]; then
    STREAMLIT_CMD="$PYTHON -m streamlit"
else
    STREAMLIT_CMD="$STREAMLIT"
fi

cd "$SCRIPT_DIR"
exec $STREAMLIT_CMD run app.py \
    --server.port 5000 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
