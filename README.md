# nvidia-smi-web-agent

An HTTP agent (FastAPI) that exposes realtime NVIDIA GPU metrics and running process information via simple JSON endpoints. It is intended to be deployed on GPU hosts and queried by a lightweight web UI or monitoring system. Internally it leverages the excellent `nvitop` library (NVML) instead of shelling out to `nvidia-smi`, providing lower overhead and structured data.

## ✨ Features

- GPU inventory (`/count`) and detailed status (`/status`)
- Per‑GPU metrics: name, fan speed, temperature, power, utilization, memory total / used / free, memory utilization %, timestamp
- Per process information (PID, user, command, GPU memory) with filtering by process type (`C`, `G`, `NA`)
- Optional lightweight token header authentication (static token)
- Configurable URL prefix for multi‑host aggregation behind a reverse proxy
- Docker image & systemd service example
- Zero external database — all in‑memory and on-demand calls to NVML

## 🚀 Quick Start (Local - uv)

The project uses [uv](https://docs.astral.sh/uv/) for fast Python dependency & virtualenv management.

Install uv (if not already):
```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```
(On Windows PowerShell)
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Clone the repo:
```bash
git clone https://github.com/nvidia-smi-web/agent.git nvidia-smi-web-agent
cd nvidia-smi-web-agent
```

Sync venv and run:
```bash
uv sync
uv run main.py
```

Open: `http://localhost:8000/status`

You can copy .env.example to .env and edit as needed. Refer to the Configuration section below.

## 🐳 Docker (Recommended for deployment)

Build (local):
```bash
docker build -t do1e/nvidia-smi-web-agent .
```

Or pull prebuilt image:
```bash
docker pull do1e/nvidia-smi-web-agent
```

Run (with GPU access):
```bash
docker run -d \
    --name nvidia-smi-web-agent \
    -e TOKEN=changeme \
    -e URL_PREFIX=server1 \
    -p 8000:8000 \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    --gpus=all \
    --pid=host \
    --restart unless-stopped \
    do1e/nvidia-smi-web-agent
```

Test:
```bash
curl -H "Authorization: changeme" http://localhost:8000/server1/status
```

## 🛠 systemd Example

Run as root:
```bash
git clone https://github.com/nvidia-smi-web/agent.git /opt/nvidia-smi-web-agent
cd /opt/nvidia-smi-web-agent
```

The repository includes `nvidia-smi-web-agent.example.service`. Edit and place into `/etc/systemd/system/nvidia-smi-web-agent.service`.Then:
```bash
systemctl daemon-reload
systemctl enable --now nvidia-smi-web-agent
systemctl status nvidia-smi-web-agent
```

## 🗂 Endpoints

| Method | Path                | Query Params                    | Description |
|--------|---------------------|---------------------------------|-------------|
| GET    | /count              | —                              | Return number of visible GPUs. |
| GET    | /status             | idx=0,1  (optional)             | Filter which GPU indices to include (comma separated). |
|        |                     | process=G\|C\|NA (optional)     | Filter processes by type. Empty = all. |

### Response Shapes

Successful responses follow:
```
{ "code": 0, "data": ... }
```

Errors follow:
```
{ "code": <non-zero>, "data": null, "error": "message" }
```

Example `/status` data payload:
```json
{
    "code": 0,
    "data": {
        "count": 4,
        "devices": [
            {
                "idx": 0,
                "name": "NVIDIA GeForce RTX 3090",
                "fan_speed": 51,
                "temperature": 55,
                "power_status": "119W / 350W",
                "gpu_utilization": 5,
                "memory_total_human": "24576MiB",
                "memory_used_human": "11728MiB",
                "memory_free_human": "12525MiB",
                "memory_utilization": 48,
                "ts": 1757926888733
            },
            {
                "idx": 1,
                "name": "NVIDIA GeForce RTX 3090",
                "fan_speed": 58,
                "temperature": 66,
                "power_status": "121W / 350W",
                "gpu_utilization": 5,
                "memory_total_human": "24576MiB",
                "memory_used_human": "11768MiB",
                "memory_free_human": "12485MiB",
                "memory_utilization": 48,
                "ts": 1757926888739
            },
            {
                "idx": 2,
                "name": "NVIDIA GeForce RTX 3090",
                "fan_speed": 60,
                "temperature": 60,
                "power_status": "112W / 350W",
                "gpu_utilization": 5,
                "memory_total_human": "24576MiB",
                "memory_used_human": "11768MiB",
                "memory_free_human": "12485MiB",
                "memory_utilization": 48,
                "ts": 1757926888744
            },
            {
                "idx": 3,
                "name": "NVIDIA GeForce RTX 3090",
                "fan_speed": 66,
                "temperature": 64,
                "power_status": "131W / 350W",
                "gpu_utilization": 5,
                "memory_total_human": "24576MiB",
                "memory_used_human": "11782MiB",
                "memory_free_human": "12470MiB",
                "memory_utilization": 48,
                "ts": 1757926888749
            }
        ],
        "processes": [
            {
                "idx": 0,
                "pid": 2879221,
                "username": "do1e",
                "command": "...",
                "type": "C",
                "gpu_memory": "11710MiB"
            },
            {
                "idx": 1,
                "pid": 2879221,
                "username": "do1e",
                "command": "...",
                "type": "C",
                "gpu_memory": "11750MiB"
            },
            {
                "idx": 2,
                "pid": 2879221,
                "username": "do1e",
                "command": "...",
                "type": "C",
                "gpu_memory": "11750MiB"
            },
            {
                "idx": 3,
                "pid": 2879221,
                "username": "do1e",
                "command": "...",
                "type": "C",
                "gpu_memory": "11750MiB"
            }
        ]
    }
}
```

## 🔐 Authentication

If the `TOKEN` environment variable is set, clients must send an `Authorization` header exactly equal to that token value. If `TOKEN` is empty or unset, the API is publicly accessible (not recommended).

## ⚙️ Configuration (Environment Variables)

| Variable    | Default | Description |
|-------------|---------|-------------|
| `PORT`      | `8000`  | Port exposed by the FastAPI server. |
| `URL_PREFIX`| (empty) | Optional leading path segment (without leading slash) to namespace endpoints, e.g. `server2` -> `/server2/status`. |
| `TOKEN`     | (empty) | Shared static token for header auth. Empty disables auth. |

> Note: If you set `URL_PREFIX=foo`, all documented paths gain `/foo` prefix.

## ✅ Requirements

- NVIDIA GPU + drivers installed (NVML available)
- Python 3.12+
- (Recommended) NVIDIA Container Toolkit if using Docker

## 📦 Response Codes

| code | meaning |
|------|---------|
| 0    | success |
| 1    | client input error (e.g., invalid index) |
| 2    | internal server error |
| 401  | unauthorized (token mismatch) |

## 🧾 License

Apache 2.0 License

---
Feel free to open issues or PRs for enhancements.

