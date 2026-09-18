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

## 2026-09-17 追记：黑屏事故与 LEDC 通道冲突修复

实机偶发"整屏变黑但固件仍在运行"。根因：风扇 PWM 与 BSP 背光共用了
LEDC 低速模式 TIMER_0/CHANNEL_0——背光在 app_main 里后初始化并抢占该
通道，此后 `fan_apply_level()` 的每次 duty 写入同时落在背光上；任何
风扇全速请求（手动 HIGH、STOP→运行 kick-start、故障强制全速）都会把
背光 duty 写成 0，直接黑屏。修复 77a1d15 将风扇 PWM 迁移到专用的
`LEDC_TIMER_1`/`LEDC_CHANNEL_1`（GPIO1 引脚不变），初始化顺序不再影响
结果。复测：停止状态服务 21 s 强制全速回退，故障三段转换（temp-invalid
→ endpoint-timeout → cleared）与设计一致，全程背光不受影响，见
`docs/evidence/20260917-backlight-ledc-fix.txt`。

### 追记二：STOP 档"最低转速不停转"

更换风扇实测点 STOP 后仍保持约 300 RPM。固件侧原因：原实现 STOP 用
duty 1023/1024 ≈ 99.9% 高电平，每 40 µs 周期仍有 1 tick 低脉冲，反相后
风扇收到约 0.1% 占空比，部分风扇将其解释为最低转速底限而非停转。修复：
STOP 时 `ledc_stop` 关断波形并把 GPIO1 钳在恒定高（风扇线持续拉低），
恢复运行档时重新 `ledc_channel_config` 使能输出。

**2026-09-17 晚实机复测结论：恒低电平下风扇从 1500 RPM 滑行下降，约
300 RPM 处不再下降，确认无法归零。**固件侧已做到位（STOP 期间 PWM 线
恒低、驱动完全释放），是该批风扇自身不支持 0% 占空比停转（Intel 规范
允许低占空比仅降到下限）。**已决定接受“STOP = 最低转速”语义，不加供电
切断 MOS。**另：风扇规格书标称 1500 ±10% RPM，实测满速 1350 在容差内，
转速计无 PPR 问题；CALIB 页参考值可按实测满速自行调整。

## 待新风扇到位后的遗留项

1. 校准扫描（全速参考 RPM、各档实测转速、kick-start 最低占空比），
   结果写入设置页“每扇全速参考”。
2. FAN STATUS 页 RPM/进度条/TACH OK-FAIL 与真实风扇联核。
3. 触摸导航实机走查（远程无法模拟触摸）：三键导航、设置三个标签、
   曲线/参考编辑的 ±/保存/取消、SAVED 提示、手动模式重启回自动。
4. NVS 修改 → 重启持久化核验。
5. 噪音验收与档位边界微调。

## 追记三：满速档转速显示跳动（2026-09-18）

用户录屏发现 HIGH 档（PWM 100%）时 FAN1 显示转速在 1350 与 380 之间以
约 2-4 秒周期跳动。物理上风扇不可能 1 秒内掉 70% 转速，固件加窗调试
（每秒脉冲计数）证实：空闲时段 40 个窗口全部干净（delta 45-47、
elapsed 1.0s），跳动源于 tach 信号本身在负载时段出现 1-2 秒的脉冲丢失
（suspect：整机 GPU 负载爆发耦合到 tach 线；revB 转接板的上拉
R4/R6 参考显示板 3V3）。测速算法账目核对无缺陷，但顺带修复一个潜在
bug：锁获取失败时时间戳已提交而 prev 未提交，会让下个窗口读数翻倍。

固件对策（fan_tach_window）：
1. 窗口时间戳仅在拿到锁后提交，跳窗的 delta/elapsed 保持一致；
2. 驱动状态下单窗口跌幅超过显示值 40% 判为 tach 丢失，显示值保持，
   最长保持 5 窗后接受（真实故障仍会通过 tach_ok 与超时暴露），并打
   WARN 日志（"tach dropout ... holding"）作为后续定位的电信号依据。
   STOP 滑行与 kick-start 不受影响，仍显示真实值。

硬件侧若需根治可选：ESP32 引脚处 tach 线加 RC 滤波（R3/R5 串阻 +
约 1 nF 对地）或减小上拉阻值提高噪声裕量。

### 电源路径与判别实验

**供电拓扑确认：显示板 USB 电取自 gb10 整机；风扇为独立 12V 适配器
经转接板 DC5521 供电，不取自整机**（这也解释了 STOP 档 ~300 RPM 平台：
风扇始终有电，PWM 恒低即最低速）。于是负载相关的耦合路径收窄为两条：
① USB 5V → 显示板 3V3 → tach 上拉参考（R4/R6）；② 两套独立电源的地
仅在转接板桥接，整机地弹会以共模偏移叠加在 tach 电平上，把电平推出
输入阈值窗。判别实验：显示板改用独立 USB 电源供电（数据链路走 WiFi
不受影响）——若负载时段 dropout 消失则 ① 主导，根治为显示板独立供电
或 VBUS 加磁环；若仍跳动则重点考查 ②，根治为加强转接板地桥接/单点
接地，或 tach 线 RC 滤波、减小上拉阻值提高噪声裕量。
