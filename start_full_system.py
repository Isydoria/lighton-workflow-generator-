#!/usr/bin/env python3
"""
Start Full System - Docker Entry Point

This script starts both the frontend HTTP server and the FastAPI backend.
Used as the Docker container entry point.

NO EMOJIS - Windows CP1252 encoding compatibility.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Global process references for cleanup
frontend_process = None
backend_process = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("Shutdown signal received, stopping servers...")
    cleanup_processes()
    sys.exit(0)


def cleanup_processes():
    """Terminate all child processes."""
    global frontend_process, backend_process

    if frontend_process:
        print("Stopping frontend server...")
        frontend_process.terminate()
        try:
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()

    if backend_process:
        print("Stopping backend API...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()


def start_full_system():
    """Start both frontend and backend servers."""
    global frontend_process, backend_process

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        print("=" * 50)
        print("  Starting Workflow Automation System")
        print("=" * 50)
        print()

        # Get project root directory
        project_root = Path(__file__).parent

        # Start frontend HTTP server on port 3000
        print("[1/2] Starting frontend server (port 3000)...")
        frontend_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "3000"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)

        # Check if frontend started successfully
        if frontend_process.poll() is not None:
            print("ERROR: Frontend server failed to start")
            return
        print("   Frontend server started successfully")

        # Start FastAPI backend on port 8000
        print("[2/2] Starting backend API (port 8000)...")
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.index:app",
             "--host", "0.0.0.0", "--port", "8000",
             "--timeout-keep-alive", "300"],  # 5 minutes timeout for long-running AI requests
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)

        # Check if backend started successfully
        if backend_process.poll() is not None:
            print("ERROR: Backend API failed to start")
            # Read and print the error output
            stdout, stderr = backend_process.communicate()
            if stderr:
                print("=" * 50)
                print("BACKEND ERROR DETAILS:")
                print("=" * 50)
                print(stderr.decode('utf-8', errors='replace'))
                print("=" * 50)
            cleanup_processes()
            return
        print("   Backend API started successfully")

        print()
        print("=" * 50)
        print("  ALL SERVERS RUNNING")
        print("  Frontend: http://localhost:3000")
        print("  Backend API: http://localhost:8000")
        print("  API Docs: http://localhost:8000/docs")
        print("=" * 50)
        print()
        print("Press Ctrl+C to stop all servers")

        # Keep the script running and monitor processes
        while True:
            # Check if any process died
            if frontend_process.poll() is not None:
                print("ERROR: Frontend server stopped unexpectedly")
                cleanup_processes()
                sys.exit(1)

            if backend_process.poll() is not None:
                print("ERROR: Backend API stopped unexpectedly")
                cleanup_processes()
                sys.exit(1)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        cleanup_processes()
        print("All servers stopped")
    except Exception as e:
        print(f"Error: {e}")
        cleanup_processes()
        sys.exit(1)


if __name__ == "__main__":
    start_full_system()
