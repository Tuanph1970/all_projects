#!/usr/bin/env python3
"""
Quick start script for training the Vietnamese Grade 12 Math Tutor.

Usage:
    python run_train.py              # Train with defaults
    python run_train.py --dry-run    # Validate setup
    python run_train.py --epochs 3   # Custom epochs
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Change to project directory
    project_dir = Path(__file__).parent

    # Build command
    cmd = [sys.executable, "training/train.py"] + sys.argv[1:]

    print("=" * 60)
    print("Vietnamese Grade 12 Math Tutor - Training")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    # Run training
    subprocess.run(cmd, cwd=project_dir)

if __name__ == "__main__":
    main()
