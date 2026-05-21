#!/bin/bash

MODEL="hf.co/thanhdo881/qwen3-1.7b-vivu-travel-vn-GGUF:Q4_K_M"

echo "=== Buoc 1: Khoi dong server noi bo de pull model ==="
# Chay Ollama tren port noi bo 11434 truoc (port 7860 chua mo ra ngoai)
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
TEMP_PID=$!

echo "Dang doi server noi bo san sang..."
sleep 8

echo "Dang tai model: $MODEL"
OLLAMA_HOST=http://localhost:11434 ollama pull "$MODEL" && echo "Model da tai xong!" || echo "Pull that bai, tiep tuc..."

# Tat server noi bo
kill $TEMP_PID 2>/dev/null || true
sleep 3

echo "=== Buoc 2: Khoi dong server chinh tren port 7860 (model da san sang) ==="
# OLLAMA_HOST=0.0.0.0:7860 da duoc set trong Dockerfile ENV
exec ollama serve
