# GB10 cluster dashboard

The ESP32 display runs in 90-degree landscape mode at 320 x 172. The display
and AXS5106L touch coordinates use the same rotation transform from the
Waveshare BSP.

The firmware connects to Wi-Fi and reads:

```text
http://192.168.88.181:9108/status
```

The read-only service runs as a user service on `gb10`. For each host (local
head node and SSH-reachable worker) it reports:

- GPU temperature, utilization, board power (`power.draw`), current and max SM
  clocks, thermal-throttle and power-cap throttle flags, and GPU-allocated
  memory (the `--query-compute-apps` sum, `gpu_mem_mb`);
- SoC/ACPI thermal-zone peak (`cpu_temp_c`), CPU utilization, estimated
  whole-node draw (`power_sys_est_w`, modeled after the sparkDash fleet-energy
  formula and labeled as an estimate);
- RAM use plus total/available pool size, NVMe composite temperature, root
  filesystem use, disk and network throughput (kB/s), load, and uptime;
- DeepSeek running/waiting requests, KV cache use, prompt and generation token
  rates, TTFT mean (recent window, cumulative fallback) and p95, inter-token
  latency p95, preemption counter, prefix-cache hit rate, and speculative
  decoding acceptance rate.

Fields a source cannot provide are `null`, never zero-faked. The service does
not mutate model containers or deployment configuration.

## Display pages

The 320 x 172 UI uses 20 px metric text and a 24 px model-state label. It has
three pages plus a fan settings screen:

- `SYSTEM LOAD` shows GPU/SoC temperature and power, NVMe temperature, GPU
  utilization, system load, RAM use, and uptime for both hosts.
- `MODEL INFERENCE` shows service health, running and waiting requests, KV
  cache use, and prompt/generation token rates.
- `FAN STATUS` shows the shared fan stage, PWM level, control temperature,
  per-fan RPM against the configured full-speed reference, per-fan tach
  health, and a fault banner while the controller forces full speed.
- `FAN SETTINGS` edits the shared-curve stage boundaries and per-fan
  full-speed references; changes persist in NVS.

Bottom navigation switches between the three main pages. Auto rotation still
only cycles the two monitoring pages and never enters the fan page. The fan
settings screen is reachable from the gear button on `FAN STATUS` and is not
part of the browser mirror, which keeps reproducing the two monitoring pages.

The status service supplies the page interval to both clients through the
`page_rotation_ms` field. A tap anywhere on a monitoring page advances
immediately and resets the timer. The firmware falls back to ten seconds when
the field is absent or outside the supported 1-300 second range. The firmware
polls `/status` every two seconds; the mirror refreshes on the same cadence.

Wi-Fi credentials live only in the ignored file
`firmware/touch-demo/main/wifi_credentials.h`. The tracked
`wifi_credentials.example.h` documents the required defines.

## Web display mirror

Open the following URL from the LAN:

```text
http://192.168.88.181:9108/
```

The page reproduces both 320 x 172 LCD pages, scales them to fit the browser
viewport, and refreshes the same status data every two seconds. It follows the
same service-configured rotation and supports click or touch to advance. It has no
external assets or build dependencies.

## Configure page rotation

Set `--page-rotation-seconds` on the status service. Valid values are integers
from 1 through 300; the tracked service unit defaults to 5:

```text
ExecStart=/usr/bin/python3 /home/chriswang/cluster-display-status/cluster_status_server.py --host 0.0.0.0 --port 9108 --page-rotation-seconds 5
```

After changing the installed unit, reload and restart only this user service:

```bash
systemctl --user daemon-reload
systemctl --user restart cluster-display-status.service
```

## Service operations

```bash
ssh gb10 'systemctl --user status cluster-display-status.service'
ssh gb10 'curl -fsS http://127.0.0.1:9108/status'
ssh gb10 'systemctl --user restart cluster-display-status.service'
```
