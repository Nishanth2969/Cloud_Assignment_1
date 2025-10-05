#!/bin/bash

set -e

echo "Creating release package for Dining Concierge..."

RELEASE_DIR="release"
RELEASE_FILE="release.zip"

if [ -d "$RELEASE_DIR" ]; then
    rm -rf "$RELEASE_DIR"
fi

if [ -f "$RELEASE_FILE" ]; then
    rm "$RELEASE_FILE"
fi

mkdir -p "$RELEASE_DIR"

echo "Copying project files..."

cp -r frontend/ "$RELEASE_DIR/"
cp -r lambda-functions/ "$RELEASE_DIR/"
cp -r other-scripts/ "$RELEASE_DIR/"
cp -r data/ "$RELEASE_DIR/" 2>/dev/null || echo "No data directory found, skipping..."

cp README.md "$RELEASE_DIR/"
cp .gitignore "$RELEASE_DIR/"

if [ -f "SUBMISSION.md" ]; then
    cp SUBMISSION.md "$RELEASE_DIR/"
fi

echo "Cleaning up unnecessary files..."

find "$RELEASE_DIR" -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$RELEASE_DIR" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_DIR" -name "venv" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_DIR" -name "env" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_DIR" -name ".env" -delete 2>/dev/null || true
find "$RELEASE_DIR" -name "*.log" -delete 2>/dev/null || true
find "$RELEASE_DIR" -name ".DS_Store" -delete 2>/dev/null || true

echo "Building frontend..."
if [ -d "$RELEASE_DIR/frontend" ] && [ -f "$RELEASE_DIR/frontend/package.json" ]; then
    cd "$RELEASE_DIR/frontend"
    npm ci --production
    npm run build
    rm -rf node_modules
    cd ../..
else
    echo "Frontend directory not found or no package.json, skipping build..."
fi

echo "Creating release archive..."
zip -r "$RELEASE_FILE" "$RELEASE_DIR" -x "*.git*" "*.DS_Store*"

echo "Cleaning up temporary directory..."
rm -rf "$RELEASE_DIR"

echo "Release package created: $RELEASE_FILE"
echo "Package size: $(du -h $RELEASE_FILE | cut -f1)"

echo "Contents of release package:"
unzip -l "$RELEASE_FILE" | head -20

echo "Release package ready for submission!"
