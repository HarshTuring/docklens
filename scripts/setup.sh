#!/bin/bash

# Define target directory
MODEL_DIR="$HOME/.u2net"

# Create directory if it doesn't exist
mkdir -p "$MODEL_DIR"

# Download the model
echo "Downloading u2net.onnx to $MODEL_DIR..."
curl -L -o "$MODEL_DIR/u2net.onnx" https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx

echo "Download complete."
