# AI OS 1-Click Cross-Platform Launcher
# Built by Rushit Khakhkhar

import os
import sys
import subprocess
import time
import webbrowser

def main():
    print('=' * 65)
    print('        AI OPERATING SYSTEM (AI OS) - 1-CLICK LAUNCHER')
    print('                 Built by Rushit Khakhkhar')
    print('=' * 65)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, 'backend')
    frontend_dir = os.path.join(base_dir, 'frontend')

    # Ensure backend .env exists
    env_path = os.path.join(backend_dir, '.env')
    example_env = os.path.join(backend_dir, '.env.example')
    if not os.path.exists(env_path):
        if os.path.exists(example_env):
            import shutil
            shutil.copy(example_env, env_path)
            print('[INFO] Created backend/.env from .env.example')
            print('[!] Please add your GEMINI_API_KEY to backend/.env')

    print('\n[1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...')
    py_executable = sys.executable
    if sys.platform == 'win32':
        subprocess.Popen(['start', 'AI OS Backend', py_executable, '-m', 'uvicorn', 'main:app', '--reload', '--port', '8000', '--host', '127.0.0.1'], shell=True, cwd=backend_dir)
    else:
        subprocess.Popen([py_executable, '-m', 'uvicorn', 'main:app', '--reload', '--port', '8000', '--host', '127.0.0.1'], cwd=backend_dir)

    print('[2/3] Starting Next.js Frontend on http://localhost:3000 ...')
    npm_cmd = 'npm.cmd' if sys.platform == 'win32' else 'npm'
    if sys.platform == 'win32':
        subprocess.Popen(['start', 'AI OS Frontend', npm_cmd, 'run', 'dev'], shell=True, cwd=frontend_dir)
    else:
        subprocess.Popen([npm_cmd, 'run', 'dev'], cwd=frontend_dir)

    print('[3/3] Waiting for servers to initialize...')
    time.sleep(5)

    print('\nOpening AI OS Dashboard in browser...')
    webbrowser.open('http://localhost:3000')

    print('=' * 65)
    print(' AI OS is running!')
    print(' - Frontend: http://localhost:3000')
    print(' - Backend API Docs: http://127.0.0.1:8000/docs')
    print('=' * 65)

if __name__ == '__main__':
    main()
