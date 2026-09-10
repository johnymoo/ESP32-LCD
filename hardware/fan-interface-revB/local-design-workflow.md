# Fan Interface RevB 本地设计与嘉立创交付流程

## 当前结论

采用“本地保存权威设计资料 + 嘉立创完成最终器件标准化、PCB 规则、DRC、Gerber/BOM/CPL 和下单校验”的流程。网页工程用于最终制造验证，不把网页 File Source 当作唯一备份。

当前目标：两层 FR-4、约 45 x 30 mm、两个 4-pin 风扇接口、两个 1x11 2.54 mm 排母直接插入 ESP32-S3-Touch-LCD-1.47-M；ESP32 由自己的 USB-C 供电，风扇电源由独立 12 V 输入供电。

## 本机和 x570

- 本机 macOS：保存参考资料、原理图/PCB 源、BOM、机械约束和导出文件。
- x570 Ubuntu：预留 `~/project/PCB` 作为第二份工程和批处理检查目录。
- macOS 已安装并验证 KiCad 10.0.6：`~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`。
- x570 已验证隔离容器 `kicad/kicad:10.0`，实际版本 10.0.5；工作目录 `~/project/PCB` 已建立。镜像 digest：`sha256:182c8005cb775a2c448a4c18681d489f1ff472a761885eba3e08b07e3c0564de`。不修改主机 APT 或现有服务。
- KiCad 10 的 `pcb import --help` 没有列出 EPRO2/EPRU；不能声称它可直接校验嘉立创原生文件。嘉立创 EDA 仍是制造主链，独立核对需使用明确支持的中间导出或审核转换器。
- 本地资料目录：`electronics/fan-interface-revB/`。

## 推荐执行顺序

1. 先冻结连接器、显示屏针脚和板框机械约束。
2. 在原理图中完成网络命名和 ERC；不要直接靠 PCB 铜线猜网络。
3. 在嘉立创执行 Design → Import Changes from Schematic，确认每个焊盘的网络名恢复。
4. 交互式绘制 Board Outline，再摆放排母、风扇座和电源座；先检查显示屏 USB-C、按键和插入高度。
5. 先布 FAN12/GND 大电流路径，再布 PWM、TACH 和 3V3；电源铜线使用明显宽于信号线的规则。
6. 运行 DRC/DFM，检查封装、孔径、丝印和 3D 插入方向。
7. 导出 Gerber、Drill、BOM、CPL，并在嘉立创下单页上传验证；停在订单确认，不付款。

## 关键网络

```text
J1.1 VIN12_RAW -> F1 -> VIN12_PROT -> D1 -> FAN12
FAN12 -> J2.2/J3.2
J2.1/J3.1 -> GND
ESP_PWM -> R1 -> Q1 gate; Q1 drain -> J2.4/J3.4 PWM_BUS
J2.3 -> R3 -> ESP_TACH1; R4 pulls ESP_TACH1 to 3V3
J3.3 -> R5 -> ESP_TACH2; R6 pulls ESP_TACH2 to 3V3
```

显示排母只接：GND、3V3、GPIO1/PWM、GPIO2/TACH1、GPIO4/TACH2。GPIO3 是 JTAG 来源 strapping pin，本版不使用。VBUS、VBAT、UART、I2C、EN 和其余 GPIO 留空。

## 嘉立创网页当前状态

- 工程：`GB10 Fan Interface RevB Direct Plug`。
- 已删除旧 J4/U1；保留 J1/J2/J3、JDISP1/JDISP2、Q1、R1-R6、C1/C2、D1/F1。
- 已从原理图同步恢复 JDISP1/JDISP2 的显示屏接口网络。
- 已替换真实 Molex 470531000 / C240840 风扇座和 DC-005-5A-2.0 / C381116 电源座；Q1 改为 AO3400A / C20917、R1 为 220 Ω / C22962。
- 2026-09-09 07:29:29 原理图 DRC：0 fatal、0 error、0 warning；10:27:50 DFM5 PCB DRC 全部 124 项检查无问题。
- 已加入屏幕安装孔、双面天线约束、双面 GND 覆铜；电容调整后重新布线、检查，并补齐接口丝印。
- 已导出 Gerber/Drill、BOM、CPL、原理图和 PCB 原生备份。独立检查通过 40 针网络、16 元件料号、排母/安装孔和 BOM/CPL 坐标一致性。
- 当前交付为 `release-20260909-dfm5/`。修复露线/丝印及F1–J1碰撞后，在线PCB/SMT DFM和模型装配检查已完成；报告时间11:46:31。剩余排母孔径、插件手焊与板边插座等提示见交付的下单核对，仍需厂方审核。
- C1/D1/Q1/J1的嘉立创模型零度与EDA不同；保留原生CPL，单独生成180°校正版并重新导入验证，不能整板镜像或全部底面旋转。
- PCB草稿已换成DFM5、用户开票/地址/联系方式齐全；45×30 mm、2层、5片、裸PCB暂估43元。未提交或付款；正式SMT报价/插件代焊承接依赖PCB订单审核。
- 本地 Gerbonara 1.6.3 / Python 3.12 可直接解析原始制造 ZIP，包括 DC 座 G85 槽孔。顶面没有贴片元件，因此不输出顶面锡膏层；底面锡膏层存在。预览需使用支持 SVG mask/filter 的渲染器，已用 libvips/librsvg 检查两面。

## 网页操作中确认的经验

- File Source 多记录之间用 `|` 分隔，最后一条记录不能有末尾 `|`；否则 Apply 报 Invalid format。
- 器件标准化必须一起替换 Device、Symbol、Footprint，并依据真实符号的 pin 端点重接网络；只改 Supplier Part 不成立。
- 换符号时同次导入的 NO_CONNECT 可能被丢弃。符号更新后再放标记，重新 DRC。
- 每次属性改变可能重建界面节点，连续操作前要重新读取状态。扩展连接中断时，Comet 原生窗口仍能操作，不必刷新丢失工作。
- 页面源下载保留库，优于仅保存文本片段；每个关键阶段保留 `.epro2` 备份。
- 电阻封装中的负 paste expansion 并不独自证明缺锡膏：本次库同时含 layer 7 的自定义锡膏 FILL，应检查导出的锡膏层，不能盲目把 expansion 改回零而产生重复开口。

## 制造前硬门槛

- 两排排母中心距 17.00 mm、2.54 mm pitch、22-pin 编号方向与 `reference/waveshare/` 资料一致。
- 风扇插座顺序明确标注为 GND / +12V / TACH / PWM。
- 12 V 反接保护、保险丝额定值与已确认风扇额定负载匹配；启动电流、热态工作和实际转速留作首板验证。
- PCB DRC、DFM、3D 插入检查全部通过；BOM 的 LCSC 编号和封装一致。
