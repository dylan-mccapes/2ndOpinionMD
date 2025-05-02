
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [ -f "/opt/homebrew/bin/python3.10" ]; then
        PYTHON_CMD="/opt/homebrew/bin/python3.10"
    elif [ -f "/usr/local/bin/python3.10" ]; then
        PYTHON_CMD="/usr/local/bin/python3.10"
    else
        PYTHON_CMD="python3"
    fi
else
    PYTHON_CMD="python"
fi

echo "Using Python command: $PYTHON_CMD"

$PYTHON_CMD -m venv venv

source venv/bin/activate

pip install -r requirements.txt

mkdir -p chroma_db

if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
OPENAI_API_KEY=your-openai-api-key-here

CHROMA_PERSIST_DIR=./chroma_db

PORT=3001
HOST=0.0.0.0
EOL
    echo ".env file created. Please update with your API keys."
fi

echo "Setup complete! You can now run the server with:"
echo "source venv/bin/activate && python api/app.py"
