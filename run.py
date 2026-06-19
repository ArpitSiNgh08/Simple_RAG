import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

def run_command(cmd, cwd=None, shell=True):
    """Run a system command and print output."""
    print(f"Running: {cmd} in {cwd or ROOT_DIR}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    if result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}")
        return False
    return True

def main():
    print("==========================================")
    print("         Simple RAG Setup & Run           ")
    print("==========================================")

    # 1. Setup Python Virtual Environment and dependencies
    venv_dir = BACKEND_DIR / ".venv"
    pip_path = venv_dir / "bin" / "pip" if os.name != "nt" else venv_dir / "Scripts" / "pip.exe"
    python_path = venv_dir / "bin" / "python" if os.name != "nt" else venv_dir / "Scripts" / "python.exe"
    
    if not venv_dir.exists():
        print("Creating Python virtual environment...")
        # Check if standard Windows python exists to avoid MinGW python issue
        standard_python = r"C:\Users\arpit\AppData\Local\Programs\Python\Python313\python.exe"
        py_cmd = f'"{standard_python}"' if os.path.exists(standard_python) else "python"
        if not run_command(f"{py_cmd} -m venv .venv", cwd=BACKEND_DIR):
            sys.exit(1)
            
    print("Upgrading pip and build tools...")
    run_command(f"{python_path} -m pip install --upgrade pip setuptools wheel", cwd=BACKEND_DIR)
    
    print("Installing backend requirements...")
    # Attempt to install package-by-package to avoid rolling back on optional build errors (like orjson)
    req_file = BACKEND_DIR / "requirements.txt"
    if req_file.exists():
        with open(req_file, "r") as f:
            for line in f:
                pkg = line.strip()
                if pkg and not pkg.startswith("#"):
                    run_command(f"{pip_path} install {pkg}", cwd=BACKEND_DIR)
    else:
        print("Error: requirements.txt not found in backend/.")
        sys.exit(1)

    # 2. Setup Frontend dependencies & build
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend dependencies (npm install)...")
        if not run_command("npm install", cwd=FRONTEND_DIR):
            print("Warning: npm install failed. Make sure Node.js is installed.")
            
    print("Building frontend (npm run build)...")
    if not run_command("npm run build", cwd=FRONTEND_DIR):
        print("Warning: Frontend build failed. Static assets might not be served correctly.")

    # 3. Ensure uploads/ and storage/ directories exist
    os.makedirs(BACKEND_DIR / "uploads", exist_ok=True)
    os.makedirs(BACKEND_DIR / "storage", exist_ok=True)

    # 4. Start FastAPI server
    print("\nStarting backend server on http://localhost:8000...")
    uvicorn_cmd = f"{python_path} -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    run_command(uvicorn_cmd, cwd=BACKEND_DIR)

if __name__ == "__main__":
    main()
