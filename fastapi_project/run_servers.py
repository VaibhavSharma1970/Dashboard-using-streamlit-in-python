import subprocess
import time

def start_fastapi():
    """Start the FastAPI server"""
    return subprocess.Popen(["uvicorn", "main:app", "--reload"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_streamlit():
    """Start the Streamlit app"""
    return subprocess.Popen(["streamlit", "run", "streamlit_app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if __name__ == "__main__":
    # Start FastAPI server
    fastapi_process = start_fastapi()
    print("FastAPI server started.")
    
    # Give FastAPI some time to start
    time.sleep(5)  # Adjust sleep time as needed

    # Start Streamlit app
    streamlit_process = start_streamlit()
    print("Streamlit app started.")

    # Wait for both processes to complete
    try:
        fastapi_process.wait()
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        fastapi_process.terminate()
        streamlit_process.terminate()


# python run_servers.py
