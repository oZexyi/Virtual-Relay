#!/usr/bin/env python3
"""
Launch script for Virtual Relay System on Render
"""
import os
import subprocess
import sys

def main():
    print("🚀 Starting Virtual Relay System on Render...")
    
    # Get port from environment variable
    port = os.getenv("PORT", "10000")
    print(f"Using port: {port}")
    
    # Set environment variables for Streamlit
    env = os.environ.copy()
    env["RENDER"] = "true"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
    
    # Build the streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the streamlit app
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
