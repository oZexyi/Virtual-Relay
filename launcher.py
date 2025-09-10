#!/usr/bin/env python3
"""
Virtual Relay System - Main Launcher
This script launches the main dashboard for the Virtual Relay System.
"""

import os
import sys

def main():
    """Main launcher function"""
    print("🚀 Starting Virtual Relay System...")
    
    # Add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    try:
        # Import and run the dashboard
        from dashboard import main as dashboard_main
        dashboard_main()
    except ImportError as e:
        print(f"❌ Error importing dashboard: {e}")
        print("Please ensure dashboard.py is in the same directory.")
    except Exception as e:
        print(f"❌ Error starting system: {e}")
        print("Please check your system configuration.")

if __name__ == "__main__":
    main()

