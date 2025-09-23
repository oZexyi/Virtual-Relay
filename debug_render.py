#!/usr/bin/env python3
"""
Debug script to understand what Render is doing
"""
import os
import sys

def main():
    print("🔍 Render Debug Information")
    print("=" * 50)
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script being run: {sys.argv[0]}")
    print(f"Command line args: {sys.argv}")
    
    print("\n📁 Files in directory:")
    for file in sorted(os.listdir('.')):
        if os.path.isfile(file):
            print(f"  📄 {file}")
        else:
            print(f"  📁 {file}/")
    
    print("\n🌍 Environment variables:")
    env_vars = ['PORT', 'RENDER', 'STREAMLIT_SERVER_HEADLESS', 'STREAMLIT_SERVER_ENABLE_CORS']
    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        print(f"  {var}: {value}")
    
    print("\n📋 Checking configuration files:")
    config_files = ['Procfile', 'render.yaml', 'Dockerfile', 'launch.py']
    for file in config_files:
        if os.path.exists(file):
            print(f"  ✅ {file} exists")
            try:
                with open(file, 'r') as f:
                    content = f.read().strip()
                    print(f"     Content: {content[:100]}...")
            except Exception as e:
                print(f"     Error reading: {e}")
        else:
            print(f"  ❌ {file} missing")
    
    print("\n🚀 Attempting to launch Streamlit...")
    try:
        import subprocess
        port = os.getenv("PORT", "10000")
        cmd = [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", port,
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false"
        ]
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd)
    except Exception as e:
        print(f"Error launching Streamlit: {e}")

if __name__ == "__main__":
    main()
