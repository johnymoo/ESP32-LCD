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

Wi-Fi credentials live only in the ignored file
`firmware/touch-demo/main/wifi_credentials.h`. The tracked
`wifi_credentials.example.h` documents the required defines.

## Web display mirror

Open the following URL from the LAN:

```text
http://192.168.88.181:9108/
```

The page reproduces the complete 320 x 172 LCD layout, scales it to fit the
browser viewport, and refreshes the same status data every two seconds. It has
no external assets or build dependencies.

## Service operations

```bash
ssh gb10 'systemctl --user status cluster-display-status.service'
ssh gb10 'curl -fsS http://127.0.0.1:9108/status'
ssh gb10 'systemctl --user restart cluster-display-status.service'
```
