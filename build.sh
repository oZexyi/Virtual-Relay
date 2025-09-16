#!/bin/bash
# Build script for Render deployment

# Force upgrade pip first
python -m pip install --upgrade pip

# Install setuptools and wheel with force reinstall
pip install --force-reinstall setuptools==68.2.2 wheel==0.41.2

# Install requirements
pip install -r requirements.txt
