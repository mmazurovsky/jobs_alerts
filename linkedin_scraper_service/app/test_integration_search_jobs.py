import pytest
import subprocess
import time
import signal
import sys
import os
from httpx import AsyncClient
from fastapi import status

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8002
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

@pytest.mark.asyncio
async def test_search_jobs_integration():
    # Set PYTHONPATH to monorepo root
    monorepo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    env = os.environ.copy()
    env["PYTHONPATH"] = monorepo_root + (":" + env.get("PYTHONPATH", ""))
    server_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:app", f"--host={SERVER_HOST}", f"--port={SERVER_PORT}"
    ], env=env)
    try:
        # Wait for the server to be ready
        for _ in range(30):
            try:
                async with AsyncClient(base_url=SERVER_URL) as ac:
                    resp = await ac.get("/docs")
                    if resp.status_code == 200:
                        break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Server did not start in time.")

        # Run the actual integration test
        params = {
            "keywords": "Software Engineer",
            "location": "USA",
            "time_period": "5 minutes",
            "job_type": ["Full-time", "Contract"],
            "remote_type": ["Remote", "Hybrid"],
        }
        async with AsyncClient(base_url=SERVER_URL, timeout=180) as ac:
            response = await ac.get("/search_jobs", params=params)
            assert response.status_code == status.HTTP_200_OK
            jobs = response.json()
            assert isinstance(jobs, list)
            assert len(jobs) > 0
            for job in jobs:
                assert "title" in job
                assert "company" in job
                assert "location" in job
                assert "link" in job
                assert "created_ago" in job
    finally:
        # Terminate the server process
        if server_proc.poll() is None:
            if os.name == "nt":
                server_proc.terminate()
            else:
                os.kill(server_proc.pid, signal.SIGTERM)
            server_proc.wait(timeout=10) 