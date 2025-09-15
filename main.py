import logging
import os
import time
import traceback

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from nvitop import Device, GpuProcess, NaType
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

URL_PREFIX = os.environ.get("URL_PREFIX", "")
if URL_PREFIX != "" and not URL_PREFIX.startswith("/"):
    URL_PREFIX = "/" + URL_PREFIX

PORT = int(os.environ.get("PORT", 8000))

TOKEN = os.environ.get("TOKEN", "") or ""
if not TOKEN:
    logging.warning("TOKEN is not set, the API is open to public access.")

logging.info(f'URL_PREFIX: "{URL_PREFIX}", PORT: "{PORT}"')

app = FastAPI()


class TokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    async def dispatch(self, request: Request, call_next):
        if self.token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != self.token:
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "data": None, "error": "Unauthorized"},
                )
        return await call_next(request)


def get_process_gpu_memory(process: GpuProcess) -> str:
    """Get the GPU memory usage of a process by its PID."""
    gpu_memory = process.gpu_memory()
    if isinstance(gpu_memory, NaType) or gpu_memory is None:
        return "N/A"
    return f"{round(gpu_memory / 1024 / 1024)}MiB"


if TOKEN:
    app.add_middleware(TokenAuthMiddleware, token=TOKEN)


@app.get(f"{URL_PREFIX}/count")
async def get_ngpus(request: Request):
    try:
        ngpus = Device.count()
        return JSONResponse(content={"code": 0, "data": ngpus})
    except Exception as e:
        return JSONResponse(
            content={"code": 2, "data": None, "error": str(e)}, status_code=500
        )


@app.get(f"{URL_PREFIX}/status")
async def get_status(request: Request):
    try:
        ngpus = Device.count()
    except Exception as e:
        return JSONResponse(
            content={"code": 2, "data": None, "error": str(e)}, status_code=500
        )

    idx = request.query_params.get("idx", None)
    if idx is not None:
        try:
            idx = idx.split(",")
            idx = [int(i) for i in idx]
            for i in idx:
                if i < 0 or i >= ngpus:
                    raise ValueError("Invalid GPU index")
        except ValueError:
            return JSONResponse(
                content={"code": 1, "data": None, "error": "Invalid GPU index"},
                status_code=400,
            )
    else:
        idx = list(range(ngpus))

    process_type = request.query_params.get("process", "")
    if process_type not in ["", "C", "G", "NA"]:
        return JSONResponse(
            content={
                "code": 1,
                "data": None,
                "error": "Invalid process type, choose from C, G, NA",
            },
            status_code=400,
        )

    try:
        devices = []
        processes = []
        for i in idx:
            device = Device(i)
            devices.append(
                {
                    "idx": i,
                    "name": device.name(),
                    "fan_speed": device.fan_speed(),
                    "temperature": device.temperature(),
                    "power_status": device.power_status(),
                    "gpu_utilization": device.gpu_utilization(),
                    "memory_total_human": f"{round(device.memory_total() / 1024 / 1024)}MiB",
                    "memory_used_human": f"{round(device.memory_used() / 1024 / 1024)}MiB",
                    "memory_free_human": f"{round(device.memory_free() / 1024 / 1024)}MiB",
                    "memory_utilization": round(
                        device.memory_used() / device.memory_total() * 100
                    ),
                    "ts": round(time.time() * 1000),
                }
            )
            now_processes = device.processes()
            sorted_pids = sorted(now_processes)
            for pid in sorted_pids:
                process = now_processes[pid]
                if process_type == "" or process_type in process.type:
                    processes.append(
                        {
                            "idx": i,
                            "pid": process.pid,
                            "username": process.username(),
                            "command": process.command(),
                            "type": process.type,
                            "gpu_memory": get_process_gpu_memory(process),
                        }
                    )
        return JSONResponse(
            content={
                "code": 0,
                "data": {"count": ngpus, "devices": devices, "processes": processes},
            }
        )
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            content={"code": 2, "data": None, "error": str(e)}, status_code=500
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=False)
