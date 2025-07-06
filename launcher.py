#!/usr/bin/env python3
"""
ASA Log Bot NG Launcher
Choose between Terminal UI and GUI versions
"""

import sys
import os
import subprocess


def main():
    print("ASA Log Bot NG - Launcher")
    print("=" * 40)
    print("\nSelect interface:")
    print("1. GUI (Graphical User Interface)")
    print("2. Terminal UI (Original)")
    print("3. Terminal (No UI)")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            # Launch GUI version
            print("\nLaunching GUI version...")
            try:
                subprocess.run([sys.executable, "gui_app.py"])
            except KeyboardInterrupt:
                print("\nGUI closed.")
            break
            
        elif choice == '2':
            # Launch terminal UI version
            print("\nLaunching terminal UI version...")
            try:
                subprocess.run([sys.executable, "asa_log_bot_ng.py", "--continuous"])
            except KeyboardInterrupt:
                print("\nTerminal UI closed.")
            break
            
        elif choice == '3':
            # Launch terminal no UI version
            print("\nLaunching terminal (no UI) version...")
            try:
                subprocess.run([sys.executable, "asa_log_bot_ng.py", "--continuous", "--no-ui"])
            except KeyboardInterrupt:
                print("\nTerminal version closed.")
            break
            
        elif choice == '4':
            print("\nExiting...")
            break
            
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()