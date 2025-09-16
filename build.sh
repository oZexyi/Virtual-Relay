#!/bin/bash
# Build script for Render deployment

# Upgrade pip, setuptools, and wheel first
pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt
