#!/usr/bin/env python3
import os
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont

class PlateMaker:
    def __init__(self):
        # Original configuration preserved
        self.FRAME_W, self.FRAME_H = 5_000, 4_000
        self.SIDE_PAD = 40
        self.TOP_PAD = 40
        self.BOTTOM_PAD = 40
        self.BANNER_PAD_Y = 60
        self.MAX_FONT_SIZE = 180
        self.MIN_FONT_SIZE = 40
        self.TEXT_COLOR = (0, 0, 0)
        self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        self.FALLBACK_FONTS = ("DejaVuSans-Bold.ttf", "arial.ttf")
        self.LOGO_PATH = "logo/Shobha Emboss.png"

        # rembg API config from environment
        # Default to official rembg API URL you shared if not set
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        if not self.REMBG_API_KEY:
            raise RuntimeError("REMBG_API_KEY is not set. Configure it in environment variables.")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        if status_callback:
            status_callback("📤 Reading image...")

        # Convert uploaded file-like to bytes
        if hasattr(image_file, "read"):
            img_bytes = image_file.read()
        else:
            img_bytes = image_file

        name = catalog

        if status_callback:
            status_callback("🎭 Removing background via API...")

        fg = self.remove_bg_from_bytes(img_bytes)
        fg = self.trim_transparent(fg)

        if status_callback:
            status_callback("📏 Resizing image...")

        fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)

        if status_callback:
            status_callback("🏷️ Adding logo overlay...")

        fg_canvas = Image.new("RGBA", fg.size, (0, 0, 0, 0))
        fg_canvas.paste(fg, (0, 0), fg)
        fg_canvas = self.add_logo_overlay(fg_canvas, (0, 0), (fg.width, fg.height))
        fg = fg_canvas

        if status_callback:
            status_callback("✏️ Creating banner...")

        banner_text = self.make_banner_text(name, design_number)
        font = self.best_font(banner_text, self.FRAME_W)
        tw, th = self.text_wh(banner_text, font)
        banner_h = th + 2 * self.BANNER_PAD_Y

        if status_callback:
            status_callback("🎨 Composing final image...")

        cv = self.make_canvas(banner_h)
        draw = ImageDraw.Draw(cv)

        bx = self.SIDE_PAD + (self.FRAME_W - tw) // 2
        by = self.TOP_PAD + (banner_h - th) // 2
        draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)

        sx = self.SIDE_PAD + (self.FRAME_W - fg.width) // 2
        sy = self.TOP_PAD + banner_h + (self.FRAME_H - fg.height) // 2
        cv.paste(fg, (sx, sy), fg)

        if status_callback:
            status_callback("✅ Image processing complete!")

        return cv.convert("RGB")

    def remove_bg_from_bytes(self, img_bytes: bytes) -> Image.Image:
        """
        Removes background via rembg API.

        POST {REMBG_API_URL}
        headers: {"x-api-key": REMBG_API_KEY}
        files:   {"image": <bytes>}
        """
        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}

        resp = requests.post(self.REMBG_API_URL, headers=headers, files=files, timeout=60)
        if resp.status_code == 200:
            return Image.open(BytesIO(resp.content)).convert("RGBA")
        else:
            detail = None
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text[:500]
            raise RuntimeError(f"Background removal API failed ({resp.status_code}): {detail}")

    # ---------------- Original helpers preserved ----------------

    def trim_transparent(self, img: Image.Image) -> Image.Image:
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        return img.crop(bbox) if bbox else img

    def downsize(self, img: Image.Image, box_w: int, box_h: int) -> Image.Image:
        if img.width <= box_w and img.height <= box_h:
            return img
        scale = min(box_w / img.width, box_h / img.height)
        return img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)

    def make_canvas(self, banner_h: int) -> Image.Image:
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        return Image.new("RGB", (w, h), "white")

    def add_logo_overlay(self, canvas: Image.Image, fg_pos, fg_size, size_ratio=0.20, opacity=0.31, margin=100) -> Image.Image:
        canvas = canvas.convert("RGBA")
        logo = Image.open(self.LOGO_PATH).convert("RGBA")

        target_w = int(fg_size[0] * size_ratio)
        scale = target_w / logo.width
        logo = logo.resize((target_w, int(logo.height * scale)), Image.Resampling.LANCZOS)

        alpha = logo.split()[1].point(lambda p: int(p * opacity))
        logo.putalpha(alpha)

        sx, sy = fg_pos
        fw, fh = fg_size
        lx = sx + fw - logo.width - margin
        ly = sy + fh - logo.height - margin
        canvas.paste(logo, (lx, ly), logo)
        return canvas

    def make_banner_text(self, name: str, design: str) -> str:
        return f"{name} 6.30 D.No {design}"

    def load_font(self, pts: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(
                self.FONT_PATH,
                pts,
                layout_engine=ImageFont.LAYOUT_RAQM,
                font_variation={"wght": 800, "ital": 1},
            )
        except Exception:
            try:
                return ImageFont.truetype(self.FONT_PATH, pts)
            except Exception:
                for fb in self.FALLBACK_FONTS:
                    try:
                        return ImageFont.truetype(fb, pts)
                    except OSError:
                        continue
                return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        x0, y0, x1, y1 = font.getbbox(txt)
        return x1 - x0, y1 - y0

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):
            f = self.load_font(size)
            if self.text_wh(txt, f)[0] <= max_w:
                return f
        return self.load_font(self.MIN_FONT_SIZE)
