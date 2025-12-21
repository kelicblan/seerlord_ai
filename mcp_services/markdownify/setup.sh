#!/bin/bash

echo 'prepare Unix preinstall'
echo 'Installing Python dependencies for OCR...'
echo 'Installing uv'
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
echo 'Using uv to install markitdown'
uv sync
echo 'Finished install Python dependencies'
