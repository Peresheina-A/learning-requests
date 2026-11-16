"""Запускает корпоративный сервис и AI-buddy в одном терминале."""
import subprocess
import sys
import time
from pathlib import Path

if __name__=='__main__':
    root=Path(__file__).parent
    children=[]
    try:
        children.append(subprocess.Popen([sys.executable,'-m','uvicorn','corporate_app:app','--host','127.0.0.1','--port','8001'],cwd=root/'corporate-service'))
        children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8000','--reload'],cwd=root))
        while all(p.poll() is None for p in children):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
        for p in children:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
