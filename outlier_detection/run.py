# run.py
import uvicorn
import subprocess
import sys
import os
from multiprocessing import Process

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_fastapi():
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)

def run_streamlit():
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "frontend/app.py",
        "--server.port=8501"
    ])

if __name__ == "__main__":
    # Start FastAPI server
    fastapi_process = Process(target=run_fastapi)
    fastapi_process.start()
    
    # Start Streamlit app
    streamlit_process = Process(target=run_streamlit)
    streamlit_process.start()
    
    # Wait for both processes
    fastapi_process.join()
    streamlit_process.join()