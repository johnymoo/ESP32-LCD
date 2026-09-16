# 风扇自动控制用户故事基线

- `baseline_revision: fan-control-20260916-r3`
- 权威来源：用户 2026-09-16 明确需求；现有硬件/软件事实来自 `docs/CLUSTER-DASHBOARD.md`、`hardware/fan-interface-revB/display-pinout.md` 及 2026-09-16 实测记录。
- 状态：`IMPLEMENTED_20260916`（UI 高保真原型经用户逐屏确认后实现；
  FANCTRL-04 安全边界按原型确认的"故障即全速 + 屏幕故障条 + 重启回自动"
  落地。FANCTRL-02、FANCTRL-03、FANCTRL-07 的风扇实测项待更换静音风扇后
  核验，见 `docs/FAN-CONTROL-20260916.md` 遗留清单。）

## FANCTRL-01

As an operator, I want to monitor the temperatures of both GB10 systems on the ESP32 LCD, so that I can see the thermal state that drives fan control.

- Given the ESP32 is connected to the status endpoint, when a new status sample arrives, then both GB10 temperatures and the selected control temperature are visible.

## FANCTRL-02

As an operator, I want fan speed to increase in three or four configurable stages, with the lowest stage stopped, so that cooling noise stays low until temperature requires more airflow.

- Given valid temperature samples, when the selected temperature crosses a configured stage boundary, then the shared PWM output changes to that stage and both fans follow it.
- Given the temperature falls, when it crosses the lower boundary with hysteresis, then the controller steps down without rapid oscillation.

## FANCTRL-03

As an operator, I want to edit stage temperature boundaries and fan levels from the touchscreen, so that the control curve can be tuned without reflashing firmware.

- Given the configuration screen, when I edit a boundary or fan level and save, then the new curve is shown as active and persists across restart.

## 当前范围边界

FAN1/FAN2 独立调速不属于本版范围。现有 Rev B 的 GPIO1 是两只风扇共用 PWM，GPIO2/4 只分别读取 TACH；本版采用一条共享温控曲线、两路独立 RPM 显示。

## FANCTRL-06

As an operator, I want the existing two monitoring pages to remain available while gaining a fan status page and a settings page, so that fan control does not hide the current GB10 dashboard.

- Given the existing dashboard, when I tap through pages, then `SYSTEM LOAD` and `MODEL INFERENCE` remain intact.
- Given the fan status page, when I open it, then I can see shared control state and independent FAN1/FAN2 RPM; a settings button opens fan settings without adding another main page.

## FANCTRL-07

As an operator, I want separate full-speed RPM references for FAN1 and FAN2, so that different fan models are not treated as faulty merely because their maximum RPM differs.

- Given a shared PWM stage, when both fans run, then each fan's raw RPM is displayed against its own reference; the reference does not change the shared PWM stage.

## FANCTRL-04 (安全边界，待用户确认)

Recommended behavior: if the status endpoint or either temperature becomes invalid, the controller enters a visible fault state and commands full speed; a manual mode is available but is clearly marked and exits on restart.
