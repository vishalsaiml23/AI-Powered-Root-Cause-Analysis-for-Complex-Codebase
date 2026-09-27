"""Start the Streamlit frontend."""
import subprocess, sys
subprocess.run([sys.executable, "-m", "streamlit", "run",
                "rca_frontend/app.py", "--server.port", "8501"], check=True)
