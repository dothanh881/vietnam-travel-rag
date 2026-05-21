#!/bin/bash
set -e

echo "🚀 Khởi động Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Chờ Ollama sẵn sàng
echo "⏳ Đợi Ollama khởi động..."
sleep 5
until curl -sf http://localhost:7860/ > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Ollama đã sẵn sàng!"

# Pull model nếu chưa có
MODEL="hf.co/thanhdo881/qwen3-1.7b-vivu-travel-vn-GGUF:Q4_K_M"
if ! ollama list | grep -q "qwen3-1.7b-vivu"; then
    echo "📥 Đang tải model: $MODEL ..."
    ollama pull "$MODEL"
    echo "✅ Model đã tải xong!"
else
    echo "✅ Model đã có sẵn, bỏ qua bước tải!"
fi

# Giữ server chạy
wait $OLLAMA_PID
