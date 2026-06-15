#!/bin/bash

# Khởi động thẳng server chính trên port 7860 (đã bake model vào image)
echo "=== Khoi dong Ollama Server ==="
exec ollama serve
