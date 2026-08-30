"""AIOS2 operator bootstrap launcher."""

import subprocess
import sys
import urllib.request


HOST = "127.0.0.1"
PORT = 8000


def main():
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
        check=True,
    )


if __name__ == "__main__":
    main()
