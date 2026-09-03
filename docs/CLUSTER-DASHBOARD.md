# GB10 cluster dashboard

The ESP32 display runs in 90-degree landscape mode at 320 x 172. The display
and AXS5106L touch coordinates use the same rotation transform from the
Waveshare BSP.

The firmware connects to Wi-Fi and reads:

```text
http://192.168.88.181:9108/status
```

The read-only service runs as a user service on `gb10`. It reports:

- head and worker GPU temperature, utilization, power, system load, and RAM use;
- DeepSeek running and waiting request counts;
- vLLM KV cache usage;
- recent prompt and generation token rates.

GB10 reports GPU memory fields as `N/A`, so the dashboard intentionally does
not display GPU memory usage. The service does not mutate model containers or
deployment configuration.

## Display pages

The 320 x 172 UI uses 20 px metric text and a 24 px model-state label. It has
two pages:

- `SYSTEM LOAD` shows temperature, GPU utilization, system load, RAM use, and
  power for both hosts.
- `MODEL INFERENCE` shows service health, running and waiting requests, KV
  cache use, and prompt/generation token rates.

The status service supplies the page interval to both clients through the
`page_rotation_ms` field. A tap anywhere on the active page advances
immediately and resets the timer. The firmware falls back to ten seconds when
the field is absent or outside the supported 1-300 second range.

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
from 1 through 300; the tracked service unit defaults to 10:

```text
ExecStart=/usr/bin/python3 /home/chriswang/cluster-display-status/cluster_status_server.py --host 0.0.0.0 --port 9108 --page-rotation-seconds 10
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
