"""Add a mock interface to export/topdown_scene.png. Picture only: nothing here is playable."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
img = Image.open(HERE / "export" / "topdown_scene.png").convert("RGBA")
layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
d = ImageDraw.Draw(layer)
W, H = img.size


def font(size):
    return ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", size)


def panel(box, radius=10):
    d.rounded_rectangle(box, radius, fill=(10, 18, 44, 215), outline=(103, 185, 233, 210), width=2)


def bar(x, y, w, h, share, colour):
    d.rounded_rectangle((x, y, x + w, y + h), 4, fill=(5, 8, 22, 230))
    d.rounded_rectangle((x + 2, y + 2, x + 2 + (w - 4) * share, y + h - 2), 3, fill=colour)


panel((18, 18, 348, 116))
d.rectangle((32, 32, 92, 92), fill=(44, 71, 125, 255), outline=(150, 217, 245, 255), width=2)
d.text((48, 42), "ฮู้ด", font=font(16), fill=(220, 240, 255))
d.text((106, 28), "นักล่าน้ำแข็ง  Lv. 12", font=font(18), fill=(235, 246, 255))
bar(106, 60, 226, 16, 0.78, (82, 200, 130, 255))
bar(106, 82, 226, 12, 0.52, (82, 145, 235, 255))

panel((W - 218, 18, W - 18, 218))
d.rectangle((W - 204, 32, W - 32, 204), fill=(95, 125, 175, 200))
d.line((W - 204, 150, W - 32, 88), fill=(33, 48, 92, 255), width=10)
d.ellipse((W - 124, 114, W - 112, 126), fill=(150, 225, 255, 255))
for x, y in ((W - 92, 134), (W - 72, 148), (W - 66, 112), (W - 164, 150)):
    d.rectangle((x, y, x + 7, y + 7), fill=(170, 80, 220, 255))

panel((W // 2 - 300, H - 90, W // 2 + 300, H - 18))
labels = ["ฟัน", "กวาด", "น้ำแข็ง", "พุ่ง", "ยา", "ยา", "", ""]
for i, label in enumerate(labels):
    x = W // 2 - 286 + i * 72
    d.rounded_rectangle((x, H - 78, x + 60, H - 30), 7, fill=(28, 45, 92, 255), outline=(82, 127, 196, 255), width=2)
    d.text((x + 30, H - 54), label, font=font(14), fill=(225, 240, 255), anchor="mm")

panel((18, H - 190, 390, H - 18))
for i, line in enumerate(["[เขต] ยินดีต้อนรับสู่ลานหิมะคราม", "น้ำแข็ง: ใครไปล่ามอนบ้าง", "เงาเหมันต์: รออีกหนึ่งคน", "[ระบบ] คุณได้รับ 120 EXP"]):
    d.text((34, H - 176 + i * 36), line, font=font(16), fill=(214, 232, 250))

spots = json.loads((HERE / "export" / "topdown_labels.json").read_text())
d.text(spots["hero"], "นักล่าน้ำแข็ง", font=font(18), fill=(255, 255, 255), anchor="mm", stroke_width=2, stroke_fill=(5, 10, 30))
d.text(spots["foe"], "-128", font=font(30), fill=(255, 225, 120), anchor="mm", stroke_width=3, stroke_fill=(35, 20, 50))

Image.alpha_composite(img, layer).convert("RGB").save(HERE / "export" / "topdown_mockup.png")
print("saved")
