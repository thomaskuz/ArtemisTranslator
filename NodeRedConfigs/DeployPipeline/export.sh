#!/bin/bash

# Export Pipeline: Build amd64 NodeRed image with AMQP and export for Kubernetes
# Run this when you're ready to deploy to Kubernetes (not for local development)

set -e

echo "=========================================="
echo "NodeRed Export Pipeline for Kubernetes"
echo "=========================================="
echo ""

# Get directory where script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[1/4] Building NodeRed image for amd64 architecture..."
echo "      (This may take a few minutes)"
echo ""

docker buildx build \
  --platform linux/amd64 \
  -t nodered-with-amqp:latest \
  --load \
  "$SCRIPT_DIR"

echo ""
echo "[✓] Image built successfully"
echo ""

echo "[2/4] Verifying AMQP package installation..."
docker run --rm --entrypoint npm nodered-with-amqp:latest list -g @meowwolf/node-red-contrib-amqp

echo ""
echo "[✓] AMQP package verified"
echo ""

echo "[3/4] Exporting image to tar file..."
docker save nodered-with-amqp:latest -o "$SCRIPT_DIR/nodered-with-amqp.tar"

FILE_SIZE=$(du -h "$SCRIPT_DIR/nodered-with-amqp.tar" | cut -f1)
echo "[✓] Image exported: nodered-with-amqp.tar ($FILE_SIZE)"
echo ""

echo "[4/4] Preparing for transfer..."
echo ""
echo "=========================================="
echo "Export Complete!"
echo "=========================================="
echo ""
echo "File location: $SCRIPT_DIR/nodered-with-amqp.tar"
echo "File size: $FILE_SIZE"
echo ""
echo "Next steps:"
echo "  1. Transfer file to Kubernetes environment:"
echo "     scp $SCRIPT_DIR/nodered-with-amqp.tar user@kubernetes-server:/path/to/"
echo ""
echo "  2. On Kubernetes machine, load the image:"
echo "     docker load -i nodered-with-amqp.tar"
echo ""
echo "  3. Deploy using docker-compose:"
echo "     docker-compose up -d"
echo ""
