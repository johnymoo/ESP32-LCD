from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'hardware/fan-interface-revB/release-20260909-dfm5'
OUT = ROOT / 'output/pdf/GB10-Fan-Interface-RevB-万用表首板测试指南.pdf'
TMP = ROOT / 'tmp/pdfs'
TMP.mkdir(parents=True, exist_ok=True)

font_path = '/System/Library/Fonts/STHeiti Light.ttc'
bold_path = '/System/Library/Fonts/STHeiti Medium.ttc'
pdfmetrics.registerFont(TTFont('Heiti', font_path, subfontIndex=0))
pdfmetrics.registerFont(TTFont('Heiti-Bold', bold_path, subfontIndex=0))

def imgfont(size, bold=False):
    return ImageFont.truetype(bold_path if bold else font_path, size)

def annotate(src, dst, marks):
    im = Image.open(src).convert('RGB')
    d = ImageDraw.Draw(im)
    for x, y, label, color in marks:
        r = 32
        d.ellipse((x-r, y-r, x+r, y+r), outline=color, width=7)
        d.ellipse((x-7, y-7, x+7, y+7), fill=color)
        tx, ty = x + 38, y - 22
        f = imgfont(34, True)
        box = d.textbbox((tx, ty), label, font=f)
        d.rounded_rectangle((box[0]-8, box[1]-5, box[2]+8, box[3]+5), radius=7, fill='white', outline=color, width=3)
        d.text((tx, ty), label, fill=color, font=f)
    im.save(dst, quality=95)

top = TMP / 'revB-top-test-points.jpg'
bottom = TMP / 'revB-bottom-test-points.jpg'
annotate(SRC / 'gerber-top.png', top, [
    (453, 436, 'A J1.1 12V+', '#d62828'), (257, 436, 'B J1.2 GND', '#1769aa'),
    (658, 865, 'C FAN1', '#d97706'), (1088, 865, 'D FAN2', '#d97706'),
    (505, 125, 'E JDISP1', '#6a1b9a'), (505, 687, 'F JDISP2', '#6a1b9a')])
annotate(SRC / 'gerber-bottom.png', bottom, [
    (911, 690, 'G F1', '#d62828'), (875, 435, 'H D1', '#d62828'),
    (531, 330, 'I Q1', '#6a1b9a'), (657, 225, 'J C1 +', '#1769aa'),
    (1117, 342, 'K J1', '#d97706')])

def annotate_fan_pin_numbers(path):
    """Mark the four through-hole pads in PCB top-view order.

    The bottom-mounted fan sockets are seen from the PCB top in this Gerber
    render, so the physical pad order reads 4, 3, 2, 1 from left to right.
    The table below remains the authoritative electrical pin mapping.
    """
    im = Image.open(path).convert('RGB')
    d = ImageDraw.Draw(im)
    font = imgfont(26, True)
    for xs in ([573, 657, 741, 826], [972, 1057, 1141, 1226]):
        for x, label in zip(xs, ('4', '3', '2', '1')):
            y = 865
            box = d.textbbox((x, y - 78), label, font=font, anchor='mm')
            d.rounded_rectangle((box[0] - 8, box[1] - 5, box[2] + 8, box[3] + 5), radius=7, fill='white', outline='#2e6f95', width=3)
            d.text((x, y - 78), label, fill='#14324a', font=font, anchor='mm')
            d.line((x, y - 45, x, y - 12), fill='#2e6f95', width=4)
    im.save(path, quality=95)

annotate_fan_pin_numbers(top)

def annotate_display_pin_numbers(path):
    """Mark JDISP1/JDISP2 pins 1-11 from the USB end (left to right)."""
    im = Image.open(path).convert('RGB')
    d = ImageDraw.Draw(im)
    font = imgfont(20, True)
    xs = [421, 505, 589, 674, 758, 842, 926, 1010, 1095, 1179, 1263]
    for y, label_y in ((125, 72), (687, 628)):
        for number, x in enumerate(xs, 1):
            label = str(number)
            box = d.textbbox((x, label_y), label, font=font, anchor='mm')
            d.rounded_rectangle((box[0] - 5, box[1] - 3, box[2] + 5, box[3] + 3), radius=5, fill='white', outline='#6a1b9a', width=2)
            d.text((x, label_y), label, fill='#4a126f', font=font, anchor='mm')
            d.line((x, label_y + (18 if y == 125 else -18), x, y + (-10 if y == 125 else 10)), fill='#6a1b9a', width=2)
    im.save(path, quality=95)

annotate_display_pin_numbers(top)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='CNTitle', fontName='Heiti-Bold', fontSize=23, leading=29, textColor=colors.HexColor('#14324a'), spaceAfter=6))
styles.add(ParagraphStyle(name='CNH2', fontName='Heiti-Bold', fontSize=16, leading=21, textColor=colors.HexColor('#14324a'), spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name='CNBody', fontName='Heiti', fontSize=10.6, leading=14.2, textColor=colors.HexColor('#23313d'), spaceAfter=3))
styles.add(ParagraphStyle(name='CNSmall', fontName='Heiti', fontSize=9.6, leading=12.4, textColor=colors.HexColor('#465563'), spaceAfter=2))
styles.add(ParagraphStyle(name='CNHead', fontName='Heiti-Bold', fontSize=10.2, leading=13.8, textColor=colors.white))
styles.add(ParagraphStyle(name='CNWarn', fontName='Heiti-Bold', fontSize=10.2, leading=13.5, textColor=colors.HexColor('#9b2c2c'), backColor=colors.HexColor('#fff1f0'), borderColor=colors.HexColor('#f2b8b5'), borderWidth=.5, borderPadding=7, spaceBefore=5, spaceAfter=6))

def P(s, style='CNBody'):
    return Paragraph(s, styles[style])

def N(items, style='CNSmall'):
    """Render compact numbered checks as a single aligned paragraph."""
    return P('<br/>'.join(f'<b>{i}.</b> {text}' for i, text in enumerate(items, 1)), style)

def hfooter(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#c9d6df'))
    canvas.line(15*mm, 12*mm, 195*mm, 12*mm)
    canvas.setFont('Heiti', 7.5)
    canvas.setFillColor(colors.HexColor('#627381'))
    canvas.drawString(15*mm, 7*mm, 'GB10 Fan Interface Rev B | 首板手焊测试')
    canvas.drawRightString(195*mm, 7*mm, str(doc.page))
    canvas.restoreState()

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=13*mm, bottomMargin=16*mm, title='GB10 Fan Interface Rev B 万用表首板测试指南')
S = []
S += [P('GB10 Fan Interface Rev B<br/>焊后万用表首板测试指南', 'CNTitle'),
      P('给测试工程师：先断电测短路，再限流上电；任何一步异常都停止，不要继续插接风扇或 ESP32。', 'CNWarn')]
summary = [[P('<b>板卡</b>','CNSmall'), P('45 x 30 mm；风扇使用独立 12 V；ESP32-LCD 使用自己的 USB-C。','CNSmall')],
           [P('<b>核心信号</b>','CNSmall'), P('GPIO1 = 共享 PWM；GPIO2 = FAN1 TACH；GPIO4 = FAN2 TACH。','CNSmall')],
           [P('<b>风扇针序</b>','CNSmall'), P('Pin 1 GND；Pin 2 +12 V；Pin 3 TACH；Pin 4 PWM。','CNSmall')],
           [P('<b>输入测点</b>','CNSmall'), P('A = J1 Pin 1 中心正极；B = J1 Pin 2 外壳地。','CNSmall')],
           [P('<b>ESP 排针</b>','CNSmall'), P('JDISP1/JDISP2：USB 端在左，顶视左到右 Pin 1–11。','CNSmall')]]
t = Table(summary, colWidths=[29*mm,151*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e9f1f6')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#b9cbd6')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#d6e1e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
S += [t, P('1. 位置、测点与针序','CNH2'),
      RLImage(str(top), width=180*mm, height=119.9*mm),
      P('A = J1 Pin 1 中心正极，B = J1 Pin 2 外壳地；C/D = FAN1/FAN2。<b>按 PCB 顶视，风扇座焊盘左到右为 4、3、2、1；JDISP1/JDISP2 左到右为 Pin 1–11。插头按定位键和 Pin 号对接。</b>','CNSmall'),
      Spacer(1,3), RLImage(str(bottom), width=180*mm, height=119.9*mm),
      P('背面：G 为保险丝 F1，H 为反接保护二极管 D1，I 为 PWM MOSFET Q1，J 为 12 V 储能电容 C1，K 为 DC5521 输入座。','CNSmall'),
      P('2. 装配与极性','CNH2'),
      N(['焊接顺序：R1-R6、C2 → Q1、F1、D1 → C1 → J1/J2/J3 → JDISP1/JDISP2。',
         'C1 按“+”焊盘；D1 色带端为阴极 K，底面图中朝右；Q1 按丝印/焊盘方向；J1 中心正极。',
         '0603、Q1 检查桥连；排母先焊定位脚，确认 17 mm 排距、平行、垂直后再焊满。']),
      P('D1 二极管档：红表笔接阳极 A，黑表笔接阴极 K，通常约 0.2–0.5 V；反接应为 OL。在路测量可能受电容和其他路径影响。','CNSmall'),
      P('焊后放大检查 16 个器件和所有插件焊点；完成断电检查前，不得插 ESP32、风扇或 12 V。','CNWarn')]

S += [PageBreak(), P('3. 断电检查（不插 ESP32、不接风扇）','CNH2'),
      P('档位：蜂鸣档/电阻档。拔掉 12 V 与 USB-C，确认 C1 已放电后再测。','CNBody')]
rows = [[P('步骤','CNHead'),P('表笔与测量点','CNHead'),P('正常现象','CNHead')],
        [P('1','CNSmall'),P('A 12V+ 对 B GND','CNSmall'),P('不应持续蜂鸣或稳定在 0 Ω。读数先低后升，可能是电容充电。','CNSmall')],
        [P('2','CNSmall'),P('A 对 ESP32 排母 3V3、GPIO1、GPIO2、GPIO4','CNSmall'),P('均不应短路。','CNSmall')],
        [P('3','CNSmall'),P('B 对 A、3V3、GPIO1、GPIO2、GPIO4','CNSmall'),P('只应有对应电路连接，不应出现异常 0 Ω 短路。','CNSmall')],
        [P('4','CNSmall'),P('Q1 Gate 对 Source/Drain；PWM_BUS 对 GND','CNSmall'),P('不应短路。Q1 D-S 二极管档单向有压降可能正常。','CNSmall')]]
t = Table(rows, colWidths=[16*mm,76*mm,88*mm], repeatRows=1)
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#14324a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#b9cbd6')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#d6e1e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
S += [t, P('4. 检查连接器针脚','CNH2')]
conn = [[P('位置','CNHead'),P('针脚','CNHead'),P('应连接/用途','CNHead')],
        [P('FAN1 / FAN2','CNSmall'),P('1','CNSmall'),P('GND；两座的 Pin 1 应互通。','CNSmall')],
        [P('FAN1 / FAN2','CNSmall'),P('2','CNSmall'),P('FAN_12V；两座的 Pin 2 应互通。','CNSmall')],
        [P('FAN1','CNSmall'),P('3','CNSmall'),P('TACH1，单独回到 GPIO2。','CNSmall')],
        [P('FAN2','CNSmall'),P('3','CNSmall'),P('TACH2，单独回到 GPIO4；不能与 FAN1 Pin 3 短接。','CNSmall')],
        [P('FAN1 / FAN2','CNSmall'),P('4','CNSmall'),P('共享 PWM_BUS；两座的 Pin 4 应互通。','CNSmall')]]
t = Table(conn, colWidths=[38*mm,20*mm,122*mm], repeatRows=1)
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2e6f95')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#b9cbd6')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#d6e1e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
S += [t, P('若板上标识或实际连接器方向与本表不一致，停止测试并拍照记录，不要按颜色猜针脚。','CNWarn')]

S += [PageBreak(), P('5. 第一次上电（仍不插 ESP32、不接风扇）','CNH2'),
      P('使用带限流的 12 V 电源，建议限流 0.2–0.3 A；不要直接使用无法限流的高功率电源。','CNBody')]
power = [[P('动作','CNHead'),P('测量','CNHead'),P('判定','CNHead')],
         [P('1. 12 V 接 DC5521，中心正极。','CNSmall'),P('黑表笔接 B，红表笔接 A。','CNSmall'),P('电源无明显限流、冒烟、异味或异常发热。','CNSmall')],
         [P('2. 通电后测 FAN_12V。','CNSmall'),P('红表笔放在 C 或 D 的 Pin 2，黑表笔放在 Pin 1。','CNSmall'),P('约 12 V；若为 0 V，断电检查 J1/F1/D1。','CNSmall')],
         [P('3. 断电并拔除 12 V。','CNSmall'),P('再次测 A 对 B。','CNSmall'),P('没有持续短路。','CNSmall')]]
t = Table(power, colWidths=[55*mm,70*mm,55*mm], repeatRows=1)
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#14324a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#b9cbd6')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#d6e1e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
S += [t, P('6. 插 ESP32 并检查 3.3 V','CNH2'),
      N(['断开 12 V，将 ESP32 垂直插入两排 1×11 排母，确认无错位或倒插。',
         '只接 ESP32 USB-C，测 E/F 对应 3V3-GND，应约 3.3 V。',
         '12 V 不得出现在 ESP32 排母任何引脚；本板只使用 3V3、GND、GPIO1、GPIO2、GPIO4。']),
      P('本板只从 ESP32 排母使用：3V3、GND、GPIO1/PWM、GPIO2/TACH1、GPIO4/TACH2。VBUS、VBAT 和其余 GPIO 不应接到 12 V。','CNWarn'),
      P('7. 接风扇前的最后检查','CNH2'),
      N(['断电后先接一个风扇，确认定位键和 Pin 1–4。',
         '两只风扇电源并联；FAN1/FAN2 的 TACH 必须分别连接。',
         '建议先测 140 mm 风扇，再测 60 mm 台达风扇。'])]
finalrows = [[P('观察项','CNHead'),P('预期结果','CNHead')],
             [P('上电启动','CNSmall'),P('风扇应能启动；复位/控制异常时，PWM 默认回到全速保护状态。','CNSmall')],
             [P('调速','CNSmall'),P('GPIO1 控制共享 PWM；AO3400A 为开漏下拉，软件 PWM 占空比与风扇实际高电平占空比反相。','CNSmall')],
             [P('测速','CNSmall'),P('FAN1 Pin 3 进入 GPIO2，FAN2 Pin 3 进入 GPIO4；两个转速读数不能互换或同时变化。','CNSmall')],
             [P('异常处理','CNSmall'),P('任何芯片发热、风扇不转、12 V 掉压、限流或读数异常：立即断 12 V 和 USB-C，记录步骤、照片和测量值。','CNSmall')]]
t = Table(finalrows, colWidths=[38*mm,142*mm], repeatRows=1)
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2e6f95')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#b9cbd6')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#d6e1e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
S += [t, Spacer(1,5), P('<b>记录 6 项：</b>板号、焊接照片、A-B 断电阻值、FAN_12V 电压、3V3 电压、FAN1/FAN2 启动与测速结果。','CNBody'),
      P('资料来源：ESP32-LCD 仓库 hardware/fan-interface-revB，Rev B 制造图与设计输入；本指南用于首板电气筛查，不能替代示波器检查 PWM 波形或正式安规测试。','CNSmall')]
S += [PageBreak(), P('附录 A：Rev B 焊接 BOM 与下单清单','CNH2'),
      P('“单板”用于清点一片；“下单数”包含本次最小包装和余量。贴片焊底面，连接器/排母焊插件位置。','CNBody')]
bom = [[P('位号','CNHead'), P('规格/封装','CNHead'), P('单板','CNHead'), P('下单数','CNHead'), P('嘉立创料号','CNHead'), P('焊接备注','CNHead')],
       [P('R1/R3/R5','CNSmall'), P('220 Ω，0603','CNSmall'), P('3','CNSmall'), P('100','CNSmall'), P('C22962','CNSmall'), P('无极性；底面','CNSmall')],
       [P('R4/R6','CNSmall'), P('4.7 kΩ，0603','CNSmall'), P('2','CNSmall'), P('100','CNSmall'), P('C23162','CNSmall'), P('无极性；底面','CNSmall')],
       [P('R2','CNSmall'), P('100 kΩ，0603','CNSmall'), P('1','CNSmall'), P('100','CNSmall'), P('C25803','CNSmall'), P('无极性；底面','CNSmall')],
       [P('C2','CNSmall'), P('100 nF/50 V，0603','CNSmall'), P('1','CNSmall'), P('50','CNSmall'), P('C14663','CNSmall'), P('无极性；底面','CNSmall')],
       [P('C1','CNSmall'), P('100 µF/25 V，贴片铝电解','CNSmall'), P('1','CNSmall'), P('20','CNSmall'), P('C970685','CNSmall'), P('按板上 +；底面','CNSmall')],
       [P('D1','CNSmall'), P('SS34，SMA','CNSmall'), P('1','CNSmall'), P('20','CNSmall'), P('C8678','CNSmall'), P('色带端为阴极；底面','CNSmall')],
       [P('Q1','CNSmall'), P('AO3400A，SOT-23','CNSmall'), P('1','CNSmall'), P('5','CNSmall'), P('C20917','CNSmall'), P('按丝印方向；底面','CNSmall')],
       [P('F1','CNSmall'), P('自恢复保险丝，16 V/1.5 A，1206','CNSmall'), P('1','CNSmall'), P('10','CNSmall'), P('C46641031','CNSmall'), P('无极性；底面','CNSmall')],
       [P('J1','CNSmall'), P('DC-005-5A-2.0，DC5521','CNSmall'), P('1','CNSmall'), P('5','CNSmall'), P('C381116','CNSmall'), P('中心正极；插件','CNSmall')],
       [P('J2/J3','CNSmall'), P('Molex 470531000，4Pin 风扇座','CNSmall'), P('2','CNSmall'), P('5','CNSmall'), P('C240840','CNSmall'), P('Pin 1 朝外观标识；插件','CNSmall')],
       [P('JDISP1/2','CNSmall'), P('1×11，2.54 mm 排母','CNSmall'), P('2','CNSmall'), P('5','CNSmall'), P('C41417323','CNSmall'), P('17 mm 排距、平行垂直；插件','CNSmall')]]
t = Table(bom, colWidths=[27*mm, 42*mm, 13*mm, 16*mm, 25*mm, 57*mm], repeatRows=1)
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#14324a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#b9cbd6')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#d6e1e8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
S += [t, Spacer(1,7), P('<b>装配核对：</b>单板共 16 个器件：11 个底面贴片 + 5 个插件（J1、J2、J3、JDISP1、JDISP2）。测试前必须确认 C1/D1/Q1 方向、两排排母排距和两个风扇座针序。','CNWarn'),
      P('连接器针序：风扇 Pin 1 = GND，Pin 2 = +12 V，Pin 3 = TACH，Pin 4 = PWM。FAN1/FAN2 的 Pin 3 不得短接；Pin 4 共享 PWM。','CNBody'),
      P('料号仅用于本次 Rev B 备料核对；若替换器件，必须同时核对封装、尺寸、极性和引脚顺序，不要直接用同规格近似料替代。','CNSmall')]
doc.build(S, onFirstPage=hfooter, onLaterPages=hfooter)
print(OUT)
