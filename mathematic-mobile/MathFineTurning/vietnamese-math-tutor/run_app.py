#!/usr/bin/env python3
"""
Quick start script for running the Vietnamese Grade 12 Math Tutor chatbot.

Usage:
    python run_app.py                           # Run with base model
    python run_app.py --model output/final/final_model  # Run with fine-tuned model
    python run_app.py --share                   # Create public link
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Change to project directory
    project_dir = Path(__file__).parent

    # Build command
    cmd = [sys.executable, "chatbot/app.py"] + sys.argv[1:]

    print("=" * 60)
    print("Vietnamese Grade 12 Math Tutor - Chatbot")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    print("\nStarting web interface...")
    print("Open http://localhost:7860 in your browser")
    print("=" * 60)

    # Run app
    subprocess.run(cmd, cwd=project_dir)

if __name__ == "__main__":
    main()
