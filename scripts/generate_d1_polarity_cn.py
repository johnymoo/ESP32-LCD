#!/usr/bin/env python3
"""Generate the Chinese D1 polarity comparison used by the bring-up record."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PHOTO = ROOT / "docs/evidence/revb-board-photo-20260915.png"
REFERENCE = ROOT / "hardware/fan-interface-revB/release-20260909-dfm5/assembly-bottom-jlc.png"
OUTPUT = ROOT / "output/review/revb-d1-polarity-20260915.png"
FONT = "/System/Library/Fonts/STHeiti Light.ttc"
BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"


def f(size: int, bold: bool = False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def main():
    photo = Image.open(PHOTO).convert("RGB").rotate(180)
    reference = Image.open(REFERENCE).convert("RGB")
    canvas = Image.new("RGB", (1520, 735), "#f6f8fb")
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 24), "D1 / SS34：实物与装配设计对照", font=f(35, True), fill="#172234")
    draw.text((40, 73), "两图方向一致：DC 插座在右侧", font=f(25), fill="#405167")

    left = (40, 162)
    right = (790, 162)
    canvas.paste(photo.crop((565, 341, 712, 433)).resize((690, 432)), left)
    canvas.paste(reference.crop((855, 323, 1010, 420)).resize((690, 432)), right)
    draw.text((40, 120), "实物：色带在左侧（异常）", font=f(28, True), fill="#bd2635")
    draw.text((790, 120), "设计：阴极 K 色带在右侧", font=f(28, True), fill="#087a55")

    for x, color in ((left[0] + int((604 - 565) / 147 * 690), "#ea3448"),
                     (right[0] + int((979 - 855) / 155 * 690), "#13a478")):
        draw.line([(x, 610), (x, 475)], fill=color, width=6)
        draw.polygon([(x, 450), (x - 13, 478), (x + 13, 478)], fill=color)

    draw.text((40, 635), "正确方向：D1 色带端（阴极 K）朝向 DC 插座", font=f(29, True), fill="#172234")
    draw.text((40, 685), "断开 12V 和 USB 后，将实物 D1 在板面内旋转 180°，再进行通电复测。", font=f(23), fill="#405167")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
