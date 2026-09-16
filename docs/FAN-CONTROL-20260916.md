# 风扇控制固件实施记录，2026-09-16

实现 `fan-control-20260916-r3` 基线与已确认的高保真原型（r3，英文标签版）。
本轮两只 6 cm 原装风扇因噪音已拔除，待更换静音风扇后补做校准与转速实测；
固件所有不依赖风扇的验收项均已在实机通过。

## 交付范围

- **状态服务**（`server/cluster_status_server.py`）：head/worker 新增
  `nvme_temp_c`（世界可读的 hwmon nvme temp1_input，无 root）与
  `uptime_s`（/proc/uptime）。worker 走原 SSH 通道，远端命令改为 `---`
  分段快照，可选字段缺失不会错位。浏览器镜像同步这两项。
- **固件**（`firmware/touch-demo/main/`）：
  - `fan_config.c/h`：共享曲线边界 + 每扇全速参考 RPM 的 NVS 持久化
    （namespace `fanctl`，键 `b0..b3`、`r0..r1`），非法值回退默认。
  - `fan_control.c/h`：GPIO1 25 kHz 反相共置 PWM、GPIO2/4 TACH 计数、
    四档温控状态机、3°C 回差、连续 2 样本确认、STOP→运行 1 s 全速
    kick-start、故障分类与强制全速、手动模式（重启回自动）。
  - `main.c`：五页 UI（SYSTEM LOAD / MODEL INFERENCE / FAN STATUS /
    FAN SETTINGS / EDIT），底部三键导航，监控两页保留点击轮换且自动轮换
    不进入风扇页；FAN STATUS 标题栏齿轮按钮（LV_SYMBOL_SETTINGS）进入
    设置；采样周期 5 s → 2 s。
  - SYSTEM LOAD 按确认的新版式重做：SoC 温度主值 + PWR（GPU SOC 功率）、
    NVME、GPU、LOAD、RAM、UPTM 六项。GB10 无板级/墙电遥测，PWR 为
    nvidia-smi `power.draw`。

## 控制规则（默认值）

`STOP 0% ≤45°C`、`LOW 35% ≤55°C`、`MED 65% ≤65°C`、`HIGH 100% ≤85°C`
（≥66°C 即进入 HIGH；85 为可编辑的安全上限），回差 3°C，连续 2 个样本
确认后才切档；档位占空比固定，触摸屏只编辑边界与每扇参考 RPM。

故障（温度无效 / 端点不可达 / Wi-Fi 断开 / 样本停滞 10 s）立即强制全速，
FAN STATUS 顶部显示红色故障条，恢复后自动回曲线。这是 FANCTRL-04 推荐
边界的落地，原型评审时已随安全路径一并确认。

## 实测证据

- 正常启动与故障恢复：`docs/evidence/20260916-fan-control-boot.txt`
- 故障注入（不可达端点）：`docs/evidence/20260916-fan-control-fault-injection.txt`
- 已确认的九屏效果图：`output/review/fan-console-*.png`（320×172 像素级，
  与 LVGL 布局坐标一一对应）

## 待新风扇到位后的遗留项

1. 校准扫描（全速参考 RPM、各档实测转速、kick-start 最低占空比），
   结果写入设置页“每扇全速参考”。
2. FAN STATUS 页 RPM/进度条/TACH OK-FAIL 与真实风扇联核。
3. 触摸导航实机走查（远程无法模拟触摸）：三键导航、设置三个标签、
   曲线/参考编辑的 ±/保存/取消、SAVED 提示、手动模式重启回自动。
4. NVS 修改 → 重启持久化核验。
5. 噪音验收与档位边界微调。
