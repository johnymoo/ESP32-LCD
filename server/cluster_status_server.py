#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

WORKER = "admin@192.168.88.198"
METRICS_URL = "http://127.0.0.1:8890/metrics"
MODEL_NAME = "deepseek-v4-flash-0731"
DASHBOARD_PATH = Path(__file__).with_name("dashboard.html")
PAGE_ROTATION_MS = 10000

_cache_lock = threading.Lock()
_cache_time = 0.0
_cache_payload = None
_counter_state = {}


def rotation_seconds(value):
    seconds = int(value)
    if not 1 <= seconds <= 300:
        raise argparse.ArgumentTypeError("must be between 1 and 300")
    return seconds


def run(command, timeout=3):
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip()


def parse_gpu(line):
    values = [value.strip() for value in line.split(",")]

    def number(index, cast=float):
        if index >= len(values) or values[index] in {"[N/A]", "N/A", ""}:
            return None
        return cast(float(values[index]))

    return {
        "temp_c": number(0, int),
        "gpu_util_pct": number(1, int),
        "power_w": number(2, float),
    }


def mem_used_pct(meminfo):
    fields = {}
    for line in meminfo.splitlines():
        match = re.match(r"(MemTotal|MemAvailable):\s+(\d+)", line)
        if match:
            fields[match.group(1)] = int(match.group(2))
    total = fields.get("MemTotal", 0)
    available = fields.get("MemAvailable", 0)
    if not total:
        return None
    return round((total - available) * 100.0 / total, 1)


def local_host():
    gpu = run([
        "nvidia-smi",
        "--query-gpu=temperature.gpu,utilization.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]).splitlines()[0]
    load1 = float(open("/proc/loadavg", encoding="ascii").read().split()[0])
    meminfo = open("/proc/meminfo", encoding="ascii").read()
    return {**parse_gpu(gpu), "load1": load1, "mem_used_pct": mem_used_pct(meminfo)}


def worker_host():
    output = run([
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=2",
        WORKER,
        "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw "
        "--format=csv,noheader,nounits; cat /proc/loadavg; cat /proc/meminfo",
    ], timeout=4)
    lines = output.splitlines()
    load1 = float(lines[1].split()[0])
    return {
        **parse_gpu(lines[0]),
        "load1": load1,
        "mem_used_pct": mem_used_pct("\n".join(lines[2:])),
    }


def metric_value(text, name):
    pattern = rf"^{re.escape(name)}(?:\{{[^}}]*\}})?\s+([-+0-9.eE]+)$"
    total = 0.0
    found = False
    for line in text.splitlines():
        match = re.match(pattern, line)
        if match:
            total += float(match.group(1))
            found = True
    return total if found else None


def counter_rate(name, value, now):
    previous = _counter_state.get(name)
    _counter_state[name] = (value, now)
    if previous is None or value < previous[0] or now <= previous[1]:
        return 0.0
    return round((value - previous[0]) / (now - previous[1]), 1)


def model_status(now):
    try:
        with urllib.request.urlopen(METRICS_URL, timeout=2) as response:
            metrics = response.read().decode("utf-8", errors="replace")
        running = int(metric_value(metrics, "vllm:num_requests_running") or 0)
        waiting = int(metric_value(metrics, "vllm:num_requests_waiting") or 0)
        kv = metric_value(metrics, "vllm:kv_cache_usage_perc") or 0.0
        prompt_total = metric_value(metrics, "vllm:prompt_tokens_total") or 0.0
        generation_total = metric_value(metrics, "vllm:generation_tokens_total") or 0.0
        return {
            "healthy": True,
            "name": MODEL_NAME,
            "running": running,
            "waiting": waiting,
            "kv_pct": round(kv * 100.0, 1),
            "prompt_tps": counter_rate("prompt", prompt_total, now),
            "generation_tps": counter_rate("generation", generation_total, now),
        }
    except Exception as error:
        return {
            "healthy": False,
            "name": MODEL_NAME,
            "running": 0,
            "waiting": 0,
            "kv_pct": 0.0,
            "prompt_tps": 0.0,
            "generation_tps": 0.0,
            "error": str(error),
        }


def collect():
    global _cache_payload, _cache_time
    now = time.time()
    with _cache_lock:
        if _cache_payload is not None and now - _cache_time < 2.0:
            return _cache_payload

        payload = {
            "updated": time.strftime("%H:%M:%S"),
            "page_rotation_ms": PAGE_ROTATION_MS,
            "head": None,
            "worker": None,
            "model": model_status(now),
        }
        errors = []
        for key, collector in (("head", local_host), ("worker", worker_host)):
            try:
                payload[key] = collector()
            except Exception as error:
                errors.append(f"{key}: {error}")
        if errors:
            payload["errors"] = errors

        _cache_payload = payload
        _cache_time = now
        return payload


class Handler(BaseHTTPRequestHandler):
    def send_headers(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

    def send_body(self, body, content_type):
        self.send_headers(body, content_type)
        self.wfile.write(body)

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            try:
                body = DASHBOARD_PATH.read_bytes()
            except OSError:
                self.send_error(503, "Dashboard unavailable")
                return
            self.send_headers(body, "text/html; charset=utf-8")
            return
        if path == "/health":
            body = b'{"ok":true}'
            self.send_headers(body, "application/json")
            return
        self.send_error(404)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            try:
                body = DASHBOARD_PATH.read_bytes()
            except OSError:
                self.send_error(503, "Dashboard unavailable")
                return
            self.send_body(body, "text/html; charset=utf-8")
            return
        if path not in {"/status", "/health"}:
            self.send_error(404)
            return
        payload = collect() if path == "/status" else {"ok": True}
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_body(body, "application/json")

    def log_message(self, fmt, *args):
        return


def main():
    global PAGE_ROTATION_MS
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9108)
    parser.add_argument(
        "--page-rotation-seconds",
        type=rotation_seconds,
        default=10,
        metavar="SECONDS",
        help="dashboard page rotation interval from 1 to 300 seconds (default: 10)",
    )
    args = parser.parse_args()
    PAGE_ROTATION_MS = args.page_rotation_seconds * 1000
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
