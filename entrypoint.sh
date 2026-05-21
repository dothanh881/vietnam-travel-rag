#!/bin/bash

echo "Khoi dong Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Cho Ollama thoi gian khoi dong (khong dung set -e de tranh thoat som)
echo "Doi Ollama khoi dong (10 giay)..."
sleep 10

# Kiem tra Ollama da san sang chua
MAX_WAIT=60
WAITED=0
until curl -sf http://localhost:7860/api/version > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "Ollama khong khoi dong sau ${MAX_WAIT}s, tiep tuc..."
        break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
done
echo "Ollama san sang!"

# Pull model
MODEL="hf.co/thanhdo881/qwen3-1.7b-vivu-travel-vn-GGUF:Q4_K_M"
echo "Dang tai model: $MODEL ..."
ollama pull "$MODEL"
echo "Model tai xong!"

# Giu server chay
wait $OLLAMA_PID
