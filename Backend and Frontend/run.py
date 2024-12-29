import subprocess
import time

# Commands to run
commands = [
    ["python3", "flask_api.py"],  # Flask API
    ["python3", "-m", "uvicorn", "LLM_backend.asgi:application", "--port", "8001"],  # Uvicorn on port 8001
    ["python3", "-m", "uvicorn", "LLM_backend.asgi:application", "--port", "8000"],  # Uvicorn on port 8000
    ["streamlit", "run", "Login.py"]  # Streamlit application
]

# List to hold subprocess references
processes = []

try:
    for cmd in commands:
        print(f"Starting: {' '.join(cmd)}")
        # Start each command as a subprocess
        process = subprocess.Popen(cmd)
        processes.append(process)
        time.sleep(2)  # Small delay to avoid potential conflicts on startup

    # Wait for all processes to complete
    for process in processes:
        process.wait()

except KeyboardInterrupt:
    print("\nStopping all processes...")
    for process in processes:
        process.terminate()  # Terminate all subprocesses

finally:
    print("All processes stopped.")
