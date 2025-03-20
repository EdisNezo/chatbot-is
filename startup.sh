#!/bin/bash
echo "Starting E-Learning Course Generator for Information Security"

# Check and start Ollama if it's not running
if ! pgrep -x "ollama" > /dev/null
then
    echo "Starting Ollama service..."
    ollama serve &
    sleep 5
else
    echo "Ollama service is already running."
fi

# Check if the model is available
if ! ollama list | grep -q "llama3.1"
then
    echo "Pulling llama3.1 model..."
    ollama pull llama3.1
else
    echo "Model llama3.1 is already available."
fi

# Fix the Dialog Manager code
python -c "exec(open('fix_dialog_manager.py').read()); fix_dialog_manager()"

# Fix the LLM Manager code
python -c "exec(open('fix_llm_manager.py').read()); fix_llm_manager()"

# Fix vector database permissions
echo "Setting proper permissions for vector database..."
mkdir -p ./data/vectorstore
chmod -R 777 ./data/vectorstore

# Start the application
echo "Starting application..."
python app.py