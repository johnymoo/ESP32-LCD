# RevB DFM5 首板制造交付 — 2026-09-09

当前有效版本为本目录。45×30 mm 双层板，显示模块直接插顶面两排排母，
底面连接独立 12 V 和两只四线风扇。用户已于2026-09-09 12:15:47提交
DFM5 PCB订单Y1，当前等待审核、未付款。用户随后决定买裸板自行焊接，
订单已保存为“不需要SMT”，列表显示“改为需SMT”和“48小时免费加急”。
当前裸板43元/5片，元器件另购；SMT报价与匹配仅作历史留档，不再提交。
备料、焊接和首板检查见[手焊清单](hand-assembly.md)。

在线 DRC 124 项无问题；在线 PCB/SMT DFM 已执行并归档，但仍有需按制造
工艺解释、交厂家复核的提示，不能表述为 DFM 全绿或已获工厂放行。
详见 [下单状态与 DFM 处置](order-readiness.md)。

## 下单文件

| 文件 | 用途 |
|---|---|
| `GB10-Fan-RevB-20260909.zip` | DFM5 原样 Gerber/钻孔包；与网页上传的 `GB10-Fan-RevB-DFM5-20260909.zip` 字节相同 |
| `GB10-Fan-RevB-BOM-20260909.csv` | 11种料、16件，带 LCSC 料号 |
| `GB10_Fan_RevB_CPL_JLC_20260909.csv` | 嘉立创模型方向校正版；本次在线重新导入后验证过 |
| `GB10_Fan_RevB_CPL_20260909.csv` | EDA 原生坐标，仅用于原生审计和追溯；不要与校正版混用 |
| `GB10-Fan-RevB-PCB.epro2`、`GB10-Fan-RevB-Schematic.epro2` | 含器件库的原生工程备份 |
| `native-pcb/`、`native-schematic/`、`gerber/` | 原生工程及制造 ZIP 的解压审计副本 |
| `dfm5-pcb-smt-report.pdf` | 2026-09-09 11:46:31 在线 PCB+SMT 检查报告 |
| `dfm5-pcb-report.pdf` | 同版、导入 BOM/CPL 前的 PCB 检查报告 |
| `assembly-bottom-jlc.png` | 校正 CPL 重新导入后的底面模型和 pin1 标识 |
| `manufacturing-remark.txt` | 随用户提交的PCB订单送审的300字制造审核备注 |
| `hand-assembly.md` | 当前执行方案：裸板订单状态、零售备料数量、焊接步骤及通电检查 |
| `smt-order-status.md` | 已放弃的SMT报价与匹配历史，不继续下单 |
| `smt-order-check-20260909.pdf` | SMT核对页下载结果，11种库存料、双面5片及费用；预览区为网站占位图 |
| `smt-matched-bottom.png`、`smt-quote-details.png` | 当前SMT匹配页底面模型及费用明细截图 |
| `gerber-top.png`、`gerber-bottom.png` | 制造 ZIP 直接渲染的裸板图；同名 SVG 为矢量图 |
| `*-audit.json`、`SHA256SUMS` | 网络、BOM、机械、制造一致性、丝印和坐标角度审计及文件校验和 |

CPL 实际为 UTF-16LE、Tab 分隔、CRLF 行尾。表格工具修改并逐单元格和字节
复核：只有 C1、D1、Q1、J1 的 Rotation 从 0 改为 180；其他字段未变。
这是嘉立创当前模型库的零度方向校正，不是整板镜像，不改变铜线或焊盘。
原点为板左下向右 20.30651006 mm、向上 11.78500056 mm；负坐标正常。
正式 SMT 审核仍应核对 pin1 和极性，若厂方更换模型或导入规则，不可再盲目加180°。

## 完整连接

```text
GB10 USB-C ── USB数据线 ── ESP32-S3-Touch-LCD-1.47-M USB-C
                                     │ 显示模块自身供电/通信
                                     │ 焊好的两排1×11排针
                                     ▼
                             JDISP1 / JDISP2 顶面排母

12V充电头 ── 支持12V协商的Type-C→DC5521线 ── J1 中心正极
                                                   │ F1 + D1
                                                   ├─ J2/FAN1 → TL-C14C 140mm
                                                   └─ J3/FAN2 → Delta AFB0612LB 60mm
GPIO1 ── R1 + Q1开漏输出 ─────────────────────────── 两只风扇PWM
GPIO2 ◀─ TACH1（串联电阻、3V3上拉） ──────────────── FAN1转速
GPIO4 ◀─ TACH2（串联电阻、3V3上拉） ──────────────── FAN2转速
```

风扇 4pin：1 GND、2 +12V、3 TACH、4 PWM，按针号和定位挡片对接，不能仅按
线色判断。两只电机电源并联，共享调速占空比、分别测速；使用风扇自带串接头
时也不是电气串联，不能把两个 TACH 输出并在一起。

USB端朝PCB的 `USB <` 标识，显示排针不得错一位或反插。由USB端起编号：
JDISP1.2 GND、.6 GPIO1、.7 GPIO2、.9 GPIO4；JDISP2.2/.3 GND、.4 3V3。
VBUS/VBAT NC；GPIO3 NC。3V3仅用于测速上拉，风扇12V不进入显示电源。
完整映射见 [display-pinout.md](../display-pinout.md)。

## 装配要求

- 顶面：JDISP1/JDISP2 两只排母；针距2.54 mm、排距17.00 mm、塑高8.5 mm。
- 底面：11贴片件（C1/C2、D1/F1、Q1、R1–R6），以及 J1/J2/J3 三个插件。
- 当前采用全部自行焊接，先完成底面贴片，再装插件。每片11个贴片件、5个插件；
  0603及SOT-23需镊子、助焊剂与放大观察，电容底部焊脚必要时使用热风/局部回流。
- 两排排母用定位治具或断电的显示板校平行后焊接。保持4个M2孔可用，以绝缘
  隔柱承力；隔柱长度按排针实际插合高度确定。显示模块不能带电插拔。
- C1正极、D1阴极、Q1 pin1和J1 pin1必须按焊盘网络/厂家图复核；不要只看
  3D外观。当前底面视图 C1正极和D1阴极均在右侧，见装配预览。
- J1中心正极，外壳地；开口位于板边，机壳须留插拔空间。底面DC座高11 mm、
  电容及风扇插头的空间不能忽略。板框与模型交线9 mm不是外伸9 mm。
- 排母1.00 mm孔符合厂家推荐1.02±0.05 mm。不要为消除软件提示随意缩孔。

## 首板验证与固件边界

通电前检查12V/3V3之间无短路、J1极性、排母顺序和绝缘；先用限流12V电源
连接两只风扇。铭牌总电流0.23 A，启动电流和热态温升仍需实测。
验证默认全速、25 kHz PWM、两路转速、停转报警与USB断开回退；每转脉冲数
按实物校准。Q1反相：风扇高电平占空比 = 1 − GPIO高电平占空比。

PCB提供接口；GB10温度采集、USB/Wi-Fi遥测、屏幕显示和温度调速曲线由固件/
主机软件实现。本交付不声称这些软件已完成或实物已测试。通信超时全速需要
固件主动实现，硬件下拉只保证ESP32未供电/复位时Q1默认关闭。

## 在线入口和备份

- [DFM5 PCB/SMT检查](https://www.jlc-dfm.com/order/smt-dfm-lceda?dfmPcbTaskCode=DFMP2609090176&dfmPcbUploadFileKeyId=620426712603435010)
- [嘉立创PCB订单列表](https://www.jlc.com/newOrder/#/pcb/pcbOrderList)：订单Y1，文件名GB10-Fan-RevB-DFM5-20260909；仅核对裸板审核和生产稿，不点“改为需SMT”。
- x570备份位置：`/home/chriswang/project/PCB/fan-interface-revB/release-20260909-dfm5/`。

网页会话和报价可能失效；本目录文件可重新上传。个人开票/地址/联系方式仅留
嘉立创账号中，不写入工程仓库。旧release目录为历史记录，不用于本次生产。
