#!/usr/bin/env python3
"""
Test script to verify deployment configuration
"""
import os
import sys

def main():
    print("🚀 Virtual Relay System - Deployment Test")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Files in directory: {os.listdir('.')}")
    
    # Check if key files exist
    key_files = ['app.py', 'Procfile', 'requirements.txt', 'render.yaml']
    for file in key_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
    
    # Check Procfile content
    if os.path.exists('Procfile'):
        with open('Procfile', 'r') as f:
            content = f.read().strip()
            print(f"Procfile content: {content}")
    
    print("Test completed!")

if __name__ == "__main__":
    main()
