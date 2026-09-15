from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'hardware/fan-interface-revB/release-20260909-dfm5'
OUT = ROOT / 'output/pdf/GB10-Fan-Interface-RevB-万用表首板测试指南.pdf'
TMP = ROOT / 'tmp/pdfs'; TMP.mkdir(parents=True, exist_ok=True)
FONT = '/System/Library/Fonts/STHeiti Light.ttc'; BOLD = '/System/Library/Fonts/STHeiti Medium.ttc'
pdfmetrics.registerFont(TTFont('Heiti', FONT, subfontIndex=0)); pdfmetrics.registerFont(TTFont('Heiti-Bold', BOLD, subfontIndex=0))
NAVY=colors.HexColor('#14324a'); BLUE=colors.HexColor('#2e6f95'); INK=colors.HexColor('#23313d'); MUTED=colors.HexColor('#526575'); GRID=colors.HexColor('#b9cbd6'); WARN_BG=colors.HexColor('#fff1f0'); WARN=colors.HexColor('#9b2c2c'); OK_BG=colors.HexColor('#edf7ef'); OK=colors.HexColor('#216e39')

def image_font(size,bold=False): return ImageFont.truetype(BOLD if bold else FONT,size)
def annotate(source,destination,marks):
    im=Image.open(source).convert('RGB'); d=ImageDraw.Draw(im)
    for x,y,label,color in marks:
        r=32; d.ellipse((x-r,y-r,x+r,y+r),outline=color,width=7); d.ellipse((x-7,y-7,x+7,y+7),fill=color)
        tx,ty=x+38,y-22; f=image_font(34,True); box=d.textbbox((tx,ty),label,font=f)
        d.rounded_rectangle((box[0]-8,box[1]-5,box[2]+8,box[3]+5),radius=7,fill='white',outline=color,width=3); d.text((tx,ty),label,fill=color,font=f)
    im.save(destination,quality=95)
def annotate_fan_pins(path):
    im=Image.open(path).convert('RGB'); d=ImageDraw.Draw(im); f=image_font(26,True)
    for xs in ([573,657,741,826],[972,1057,1141,1226]):
        for x,label in zip(xs,('4','3','2','1')):
            y=865; box=d.textbbox((x,y-78),label,font=f,anchor='mm'); d.rounded_rectangle((box[0]-8,box[1]-5,box[2]+8,box[3]+5),radius=7,fill='white',outline='#2e6f95',width=3)
            d.text((x,y-78),label,fill='#14324a',font=f,anchor='mm'); d.line((x,y-45,x,y-12),fill='#2e6f95',width=4)
    im.save(path,quality=95)
def annotate_display_pins(path):
    im=Image.open(path).convert('RGB'); d=ImageDraw.Draw(im); f=image_font(20,True); xs=[421,505,589,674,758,842,926,1010,1095,1179,1263]
    for y,label_y in ((125,72),(687,628)):
        for number,x in enumerate(xs,1):
            label=str(number); box=d.textbbox((x,label_y),label,font=f,anchor='mm'); d.rounded_rectangle((box[0]-5,box[1]-3,box[2]+5,box[3]+3),radius=5,fill='white',outline='#6a1b9a',width=2)
            d.text((x,label_y),label,fill='#4a126f',font=f,anchor='mm'); d.line((x,label_y+(18 if y==125 else -18),x,y+(-10 if y==125 else 10)),fill='#6a1b9a',width=2)
    im.save(path,quality=95)

top=TMP/'revB-top-test-points.jpg'; bottom=TMP/'revB-bottom-test-points.jpg'
annotate(SRC/'gerber-top.png',top,[(453,436,'A J1.1 12V+','#d62828'),(257,436,'B J1.2 GND','#1769aa'),(658,865,'C FAN1','#d97706'),(1088,865,'D FAN2','#d97706'),(505,125,'E JDISP1','#6a1b9a'),(505,687,'F JDISP2','#6a1b9a')])
annotate(SRC/'gerber-bottom.png',bottom,[(911,690,'G F1','#d62828'),(875,435,'H D1','#d62828'),(531,330,'I Q1','#6a1b9a'),(657,225,'J C1 +','#1769aa'),(1117,342,'K J1','#d97706')]); annotate_fan_pins(top); annotate_display_pins(top)

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCN',fontName='Heiti-Bold',fontSize=22,leading=27,textColor=NAVY,spaceAfter=5)); styles.add(ParagraphStyle(name='H1CN',fontName='Heiti-Bold',fontSize=16,leading=21,textColor=NAVY,spaceBefore=3,spaceAfter=6)); styles.add(ParagraphStyle(name='H2CN',fontName='Heiti-Bold',fontSize=12.5,leading=16,textColor=BLUE,spaceBefore=7,spaceAfter=4)); styles.add(ParagraphStyle(name='BodyCN',fontName='Heiti',fontSize=11,leading=15.2,textColor=INK,spaceAfter=4)); styles.add(ParagraphStyle(name='SmallCN',fontName='Heiti',fontSize=10,leading=13.5,textColor=INK,spaceAfter=2)); styles.add(ParagraphStyle(name='TinyCN',fontName='Heiti',fontSize=9,leading=12,textColor=MUTED,spaceAfter=1)); styles.add(ParagraphStyle(name='HeadCN',fontName='Heiti-Bold',fontSize=10.2,leading=13,textColor=colors.white)); styles.add(ParagraphStyle(name='WarnCN',fontName='Heiti-Bold',fontSize=10.5,leading=14.2,textColor=WARN,backColor=WARN_BG,borderColor=colors.HexColor('#f2b8b5'),borderWidth=.6,borderPadding=7,spaceBefore=4,spaceAfter=7)); styles.add(ParagraphStyle(name='OkCN',fontName='Heiti-Bold',fontSize=10.3,leading=14,textColor=OK,backColor=OK_BG,borderColor=colors.HexColor('#b6d9bd'),borderWidth=.6,borderPadding=6,spaceBefore=4,spaceAfter=6))
def P(text,style='BodyCN'): return Paragraph(text,styles[style])
def header(canvas,doc):
    canvas.saveState(); canvas.setStrokeColor(GRID); canvas.setLineWidth(.5); canvas.line(15*mm,286*mm,195*mm,286*mm); canvas.setFont('Heiti-Bold',7.5); canvas.setFillColor(MUTED); canvas.drawString(15*mm,289*mm,'GB10 Fan Interface Rev B | 现场测试工作表'); canvas.line(15*mm,12*mm,195*mm,12*mm); canvas.setFont('Heiti',8); canvas.drawString(15*mm,7*mm,'仅用于首板电气筛查 | 异常立即断电'); canvas.drawRightString(195*mm,7*mm,f'第 {doc.page} 页'); canvas.restoreState()
def grid_table(data,widths,header_color=NAVY,pad=6):
    t=Table(data,colWidths=widths,repeatRows=1); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),header_color),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOX',(0,0),(-1,-1),.6,GRID),('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor('#d4e0e7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),pad),('RIGHTPADDING',(0,0),(-1,-1),pad),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad)])); return t
def numbered(rows): return [P(f'[ ] <b>{i}.</b> {text}','BodyCN') for i,text in enumerate(rows,1)]

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=17*mm,bottomMargin=17*mm,title='GB10 Fan Interface Rev B 万用表首板测试指南'); S=[]
# 1: start page
S += [P('GB10 Fan Interface Rev B<br/>焊后万用表首板测试指南','TitleCN'),P('使用方式：一手拿表笔，另一手按本页编号执行。每完成一项就勾选；不跳步、不凭颜色猜针脚。','WarnCN'),P('0. 开始前只做三件事','H1CN')]
start=[[P('检查','HeadCN'),P('现场确认','HeadCN'),P('记录/动作','HeadCN')],[P('[ ] 断电','SmallCN'),P('12 V 已拔除；ESP32 USB-C 已拔除；C1 已放电。','SmallCN'),P('未确认断电，不得继续。','SmallCN')],[P('[ ] 工具','SmallCN'),P('万用表、合适表笔、手机/相机、限流 12 V 电源。','SmallCN'),P('档位：蜂鸣/电阻/二极管/直流电压。','SmallCN')],[P('[ ] 识别','SmallCN'),P('先看第 2 页图片，再找 A-K 测点；插头按 Pin 号和定位键。','SmallCN'),P('板号：____________  操作者：____________','SmallCN')]]
S += [grid_table(start,[25*mm,91*mm,64*mm]),P('1. 你会反复用到的针序','H1CN')]
pins=[[P('对象','HeadCN'),P('Pin 1','HeadCN'),P('Pin 2','HeadCN'),P('Pin 3','HeadCN'),P('Pin 4','HeadCN')],[P('FAN1 / FAN2','SmallCN'),P('GND','SmallCN'),P('+12 V','SmallCN'),P('TACH（各自独立）','SmallCN'),P('PWM（两座共享）','SmallCN')],[P('ESP32 排针','SmallCN'),P('按顶视左到右 1','SmallCN'),P('按顶视左到右 2','SmallCN'),P('...','SmallCN'),P('...','SmallCN')]]
S += [grid_table(pins,[34*mm,34*mm,34*mm,41*mm,37*mm],BLUE),P('本板使用 ESP32 的 3V3、GND、GPIO1/PWM、GPIO2/TACH1、GPIO4/TACH2。12 V 不得进入 ESP32 排针。','WarnCN'),P('2. 快速判定规则','H1CN')]
rules=[[P('看到','HeadCN'),P('立刻做','HeadCN')],[P('持续蜂鸣、稳定 0 Ω、芯片发热、冒烟、异味','SmallCN'),P('立即断开 12 V 和 USB-C；保留表笔位置，记录测点和照片。','SmallCN')],[P('FAN_12V = 0 V','SmallCN'),P('断电后回到 J1、F1、D1 路径，不插 ESP32 和风扇继续试。','SmallCN')],[P('针脚方向不确定','SmallCN'),P('停止；翻到第 2 页确认顶视方向，不按线色或插头外形猜。','SmallCN')]]
S += [grid_table(rules,[65*mm,115*mm]),Spacer(1,5),P('开始条件：以上 3 项已确认，且第 2 页的 A-K 测点和针序能在实物上找到。','OkCN'),P('本页现场备注','H2CN')]
notes = [[P('时间/环境','HeadCN'),P('备注','HeadCN')],[P('________________','SmallCN'),P('______________________________________________________________','SmallCN')],[P('________________','SmallCN'),P('______________________________________________________________','SmallCN')],[P('________________','SmallCN'),P('______________________________________________________________','SmallCN')]]
S += [grid_table(notes,[40*mm,140*mm],header_color=BLUE)]
# 2: visual map
S += [PageBreak(),P('3. 先看图，再拿表笔','H1CN'),P('所有标记均按 PCB 顶视/底视说明使用。图片用于找位置；电气定义以第 1、3、4 页表格为准。','BodyCN'),RLImage(str(top),width=150*mm,height=99.9*mm),P('顶视：A = J1 Pin 1 中心正极；B = J1 Pin 2 外壳地；C/D = FAN1/FAN2；E/F = ESP32 两排排针。风扇座焊盘按顶视左到右为 <b>4、3、2、1</b>；排针按 USB 端在左、左到右 Pin 1-11。','SmallCN'),Spacer(1,3),RLImage(str(bottom),width=150*mm,height=99.9*mm),P('底视：G = F1；H = D1；I = Q1；J = C1 正极；K = J1。翻面后不要把左/右直接套用到顶视。','SmallCN'),P('D1 极性：色带端是阴极 K，设计底面图中朝向 DC 插座一侧；C1 按板上“+”焊盘。','WarnCN')]
# 3: assembly and off checks
S += [PageBreak(),P('4. 装配、极性与断电检查','H1CN'),P('顺序固定为：先断电核对，再测短路；本页完成前不插 ESP32、不接风扇、不接 12 V。','WarnCN'),P('4.1 装配核对','H2CN')]
assembly=[[P('编号','HeadCN'),P('检查动作','HeadCN'),P('结果/备注','HeadCN')],[P('[ ] 1','SmallCN'),P('R1-R6、C2：无漏焊、桥连；位号与阻值对应。','SmallCN'),P('____________________________','SmallCN')],[P('[ ] 2','SmallCN'),P('Q1、F1、D1：方向、焊盘、相邻铜箔无桥连。','SmallCN'),P('____________________________','SmallCN')],[P('[ ] 3','SmallCN'),P('C1：负极/正极方向正确；正极对应 J 标记。','SmallCN'),P('____________________________','SmallCN')],[P('[ ] 4','SmallCN'),P('J1/J2/J3/JDISP1/JDISP2：定位脚、垂直度、排距和焊点。','SmallCN'),P('____________________________','SmallCN')]]
S += [grid_table(assembly,[22*mm,105*mm,53*mm]),P('4.2 断电短路检查','H2CN'),P('档位：蜂鸣/电阻。黑表笔先接 B 或 GND，红表笔按表格移动。电容充电造成的读数变化不等于短路；持续蜂鸣或稳定 0 Ω 才是异常。','BodyCN')]
off=[[P('编号','HeadCN'),P('红表笔测点','HeadCN'),P('正常判定','HeadCN'),P('实测值/勾选','HeadCN')],[P('[ ] 5','SmallCN'),P('A（12V+）对 B（GND）','SmallCN'),P('不应持续蜂鸣或稳定 0 Ω。','SmallCN'),P('____________','SmallCN')],[P('[ ] 6','SmallCN'),P('A 对 3V3、GPIO1、GPIO2、GPIO4','SmallCN'),P('均不应短路。','SmallCN'),P('____________','SmallCN')],[P('[ ] 7','SmallCN'),P('Q1 Gate 对 Source/Drain；PWM_BUS 对 GND','SmallCN'),P('不应短路；Q1 D-S 二极管档单向压降可能正常。','SmallCN'),P('____________','SmallCN')],[P('[ ] 8','SmallCN'),P('D1 二极管档：红笔 A、黑笔 K；再反接','SmallCN'),P('正向通常约 0.2-0.5 V；反向 OL。','SmallCN'),P('正向_____ 反向_____','SmallCN')]]
S += [grid_table(off,[20*mm,60*mm,68*mm,32*mm]),P('断电检查结论： [ ] 通过，进入第 4 页    [ ] 异常，停在此处并记录：____________________________','OkCN')]
# 4: mapping and first power
S += [PageBreak(),P('5. 连接器核对与第一次上电','H1CN'),P('先核对 Pin 1-4，再上电。第一次上电不插 ESP32、不接风扇，只验证 12 V 电源路径。','WarnCN'),P('5.1 连接器电气映射','H2CN')]
conn=[[P('位置','HeadCN'),P('Pin','HeadCN'),P('应连接/用途','HeadCN'),P('现场确认','HeadCN')],[P('FAN1 / FAN2','SmallCN'),P('1','SmallCN'),P('GND；两座 Pin 1 互通。','SmallCN'),P('[ ]','SmallCN')],[P('FAN1 / FAN2','SmallCN'),P('2','SmallCN'),P('FAN_12V；两座 Pin 2 互通。','SmallCN'),P('[ ]','SmallCN')],[P('FAN1','SmallCN'),P('3','SmallCN'),P('TACH1，单独回 GPIO2。','SmallCN'),P('[ ]','SmallCN')],[P('FAN2','SmallCN'),P('3','SmallCN'),P('TACH2，单独回 GPIO4；不能与 FAN1 Pin 3 短接。','SmallCN'),P('[ ]','SmallCN')],[P('FAN1 / FAN2','SmallCN'),P('4','SmallCN'),P('共享 PWM_BUS；两座 Pin 4 互通。','SmallCN'),P('[ ]','SmallCN')]]
S += [grid_table(conn,[36*mm,17*mm,103*mm,24*mm],BLUE),P('5.2 受控上电','H2CN')]
power=[[P('动作','HeadCN'),P('表笔位置','HeadCN'),P('正常结果','HeadCN'),P('实测/勾选','HeadCN')],[P('[ ] 1. 接 12 V 到 DC5521','SmallCN'),P('黑笔 B，红笔 A','SmallCN'),P('无明显限流、冒烟、异味、异常发热。','SmallCN'),P('____________','SmallCN')],[P('[ ] 2. 测 FAN_12V','SmallCN'),P('红笔 C/D 的 Pin 2；黑笔 Pin 1','SmallCN'),P('约 12 V。若 0 V，立即断电回查 J1/F1/D1。','SmallCN'),P('_____ V','SmallCN')],[P('[ ] 3. 断电并拔 12 V','SmallCN'),P('再次测 A 对 B','SmallCN'),P('没有持续短路。','SmallCN'),P('____________','SmallCN')]]
S += [grid_table(power,[54*mm,55*mm,54*mm,27*mm]),P('电源路径记录：J1.1 -> F1 -> D1 -> FAN12；J1.2 -> GND。D1 反向、F1 断路或焊点虚焊都会使 FAN_12V 测不到正常电压。','WarnCN'),P('本页结论： [ ] FAN_12V 正常，进入第 5 页    [ ] FAN_12V 异常，停机并拍照','OkCN')]
# 5: esp and fan
S += [PageBreak(),P('6. 接 ESP32、风扇与启动观察','H1CN'),P('只有第 4 页 FAN_12V 通过后才执行本页。接线时保持 12 V 断开，接好后再分别插 USB-C 与 12 V。','WarnCN'),P('6.1 ESP32 插接','H2CN'),*numbered(['断开 12 V；ESP32 垂直插入两排 1×11 排母，确认无错位、倒插或悬空针脚。','只接 ESP32 USB-C；测 E/F 对应 3V3-GND，记录约 3.3 V。','测 ESP32 排针，确认没有 12 V；本板仅使用 3V3、GND、GPIO1、GPIO2、GPIO4。']),P('3V3 实测：________ V    ESP32 USB/串口识别： [ ] 是  [ ] 否','BodyCN'),P('6.2 风扇插接','H2CN'),*numbered(['断开 USB-C 与 12 V，先接 FAN1；定位键对准，Pin 1-4 对照第 1 页。','再接 FAN2；两只风扇的 Pin 3 必须分别接 TACH1/TACH2。','确认风扇不会碰到外壳、线材或表笔；所有测量点已移开后再上电。']),P('风扇型号/位置：FAN1 ____________________    FAN2 ____________________','BodyCN'),P('6.3 启动与调速观察','H2CN')]
run=[[P('观察项','HeadCN'),P('预期结果','HeadCN'),P('现场记录','HeadCN')],[P('启动','SmallCN'),P('风扇应启动；若不转，先断 12 V，不等待、不反复插拔。','SmallCN'),P('[ ] 正常  [ ] 异常<br/>备注：________','SmallCN')],[P('调速','SmallCN'),P('GPIO1 控制共享 PWM；AO3400A 为开漏下拉，软件占空比与风扇高电平占空比反相。','SmallCN'),P('[ ] 有变化  [ ] 无变化','SmallCN')],[P('测速','SmallCN'),P('FAN1 Pin 3 -> GPIO2；FAN2 Pin 3 -> GPIO4；两路读数不可互换。','SmallCN'),P('FAN1：_____ RPM<br/>FAN2：_____ RPM','SmallCN')],[P('异常','SmallCN'),P('芯片发热、风扇不转、12 V 掉压、限流或读数异常：立即断 12 V 和 USB-C。','SmallCN'),P('步骤号：_____<br/>测点：_____','SmallCN')]]
S += [grid_table(run,[30*mm,98*mm,62*mm],BLUE),P('重要：ESP32 日志出现 0 RPM 只说明没有检测到有效 TACH 脉冲，不能替代 FAN_12V 电压、PWM 波形或线路连续性测量。','WarnCN'),P('本页结论： [ ] 两路启动/测速均正常    [ ] 异常，停止并转入故障记录','OkCN')]
# 6: fault and BOM
S += [PageBreak(),P('7. 故障记录与物料核对','H1CN'),P('遇到异常先断电，再填写本页。记录比“重新试一次”更重要；不要在原因不明时改变多个接线点。','WarnCN'),P('7.1 故障记录（每次异常一行）','H2CN')]
fault=[[P('步骤','HeadCN'),P('测点/针脚','HeadCN'),P('档位/实测值','HeadCN'),P('照片/处理','HeadCN')]]
for _ in range(6): fault.append([P('________','SmallCN'),P('________________','SmallCN'),P('________________','SmallCN'),P('________________________','SmallCN')])
S += [grid_table(fault,[22*mm,43*mm,49*mm,66*mm]),P('7.2 Rev B BOM（清点一片）','H2CN'),P('贴片焊底面；J1/J2/J3/JDISP1/JDISP2 为插件。下单数是本次备料数量，不等于单板用量。','SmallCN')]
bom=[[P('位号','HeadCN'),P('规格/封装','HeadCN'),P('单板','HeadCN'),P('下单','HeadCN'),P('料号','HeadCN'),P('方向/备注','HeadCN')],[P('R1/R3/R5','TinyCN'),P('220 Ω，0603','TinyCN'),P('3','TinyCN'),P('100','TinyCN'),P('C22962','TinyCN'),P('无极性；底面','TinyCN')],[P('R4/R6','TinyCN'),P('4.7 kΩ，0603','TinyCN'),P('2','TinyCN'),P('100','TinyCN'),P('C23162','TinyCN'),P('无极性；底面','TinyCN')],[P('R2','TinyCN'),P('100 kΩ，0603','TinyCN'),P('1','TinyCN'),P('100','TinyCN'),P('C25803','TinyCN'),P('无极性；底面','TinyCN')],[P('C2','TinyCN'),P('100 nF/50 V，0603','TinyCN'),P('1','TinyCN'),P('50','TinyCN'),P('C14663','TinyCN'),P('无极性；底面','TinyCN')],[P('C1','TinyCN'),P('100 µF/25 V','TinyCN'),P('1','TinyCN'),P('20','TinyCN'),P('C970685','TinyCN'),P('按板上 +；底面','TinyCN')],[P('D1','TinyCN'),P('SS34，SMA','TinyCN'),P('1','TinyCN'),P('20','TinyCN'),P('C8678','TinyCN'),P('色带为 K；底面','TinyCN')],[P('Q1','TinyCN'),P('AO3400A，SOT-23','TinyCN'),P('1','TinyCN'),P('5','TinyCN'),P('C20917','TinyCN'),P('按丝印；底面','TinyCN')],[P('F1','TinyCN'),P('16 V/1.5 A，1206','TinyCN'),P('1','TinyCN'),P('10','TinyCN'),P('C46641031','TinyCN'),P('无极性；底面','TinyCN')],[P('J1','TinyCN'),P('DC-005-5A-2.0','TinyCN'),P('1','TinyCN'),P('5','TinyCN'),P('C381116','TinyCN'),P('中心正极；插件','TinyCN')],[P('J2/J3','TinyCN'),P('Molex 470531000，4Pin','TinyCN'),P('2','TinyCN'),P('5','TinyCN'),P('C240840','TinyCN'),P('Pin 1 按图；插件','TinyCN')],[P('JDISP1/2','TinyCN'),P('1×11，2.54 mm','TinyCN'),P('2','TinyCN'),P('5','TinyCN'),P('C41417323','TinyCN'),P('17 mm；插件','TinyCN')]]
S += [grid_table(bom,[25*mm,42*mm,13*mm,14*mm,25*mm,61*mm],pad=4),Spacer(1,5),P('最终签核：断电短路 [ ]    FAN_12V [ ]    3V3 [ ]    风扇启动 [ ]    两路 TACH [ ]','OkCN'),P('资料来源：ESP32-LCD / hardware/fan-interface-revB。本文是首板电气筛查工作表，不替代示波器 PWM 检查或正式安规测试。','TinyCN')]

doc.build(S,onFirstPage=header,onLaterPages=header); print(OUT)
