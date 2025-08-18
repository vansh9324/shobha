#!/usr/bin/env python3
import os
import time
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
        self.FALLBACK_FONTS = ("DejaVuSans-Bold.ttf", "arial.ttf", "Arial.ttf")
        self.LOGO_PATH = "logo/Shobha Emboss.png"

        # rembg API config from environment
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        print(f"🔤 Font path: {self.FONT_PATH}")
        print(f"🖼️ Logo path: {self.LOGO_PATH}")
        print(f"🔑 REMBG API key present: {bool(self.REMBG_API_KEY)}")

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
            status_callback("🎭 Removing background...")

        # Try API first, fallback if fails
        try:
            fg = self.remove_bg_from_bytes(img_bytes)
        except Exception as e:
            print(f"Background removal API failed: {e}")
            if status_callback:
                status_callback("🎭 Using fallback background removal...")
            fg = self.fallback_bg_removal(img_bytes)

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
        """Remove background via rembg API with retries"""
        if not self.REMBG_API_KEY:
            raise RuntimeError("REMBG API key not configured")

        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}

        for attempt in range(3):
            try:
                resp = requests.post(
                    self.REMBG_API_URL, 
                    headers=headers, 
                    files=files, 
                    timeout=30
                )
                
                if resp.status_code == 200:
                    return Image.open(BytesIO(resp.content)).convert("RGBA")
                elif resp.status_code == 429:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                
                print(f"rembg API returned {resp.status_code}: {resp.text[:200]}")
                
            except requests.exceptions.Timeout:
                print(f"rembg API timeout (attempt {attempt + 1}/3)")
                if attempt < 2:
                    time.sleep(1)
                    continue
            except requests.exceptions.RequestException as e:
                print(f"rembg API request error: {e}")
                if attempt < 2:
                    time.sleep(1)
                    continue

        raise RuntimeError("Background removal API failed after 3 attempts")

    def fallback_bg_removal(self, img_bytes: bytes) -> Image.Image:
        """Fallback: Simple white/light background removal"""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            data = img.getdata()
            new_data = []
            
            for item in data:
                if item[0] > 240 and item[11] > 240 and item[12] > 240:
                    new_data.append((255, 255, 255, 0))  # Transparent
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            return img
            
        except Exception as e:
            print(f"Fallback background removal failed: {e}")
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            return img

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
        
        try:
            # Check if logo file exists
            if not os.path.exists(self.LOGO_PATH):
                print(f"⚠️ Logo file not found: {self.LOGO_PATH}")
                return canvas
                
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            target_w = int(fg_size[0] * size_ratio)
            scale = target_w / logo.width
            logo = logo.resize((target_w, int(logo.height * scale)), Image.Resampling.LANCZOS)

            if logo.mode == "RGBA":
                alpha = logo.split()[13].point(lambda p: int(p * opacity))
                logo.putalpha(alpha)

            sx, sy = fg_pos
            fw, fh = fg_size
            lx = sx + fw - logo.width - margin
            ly = sy + fh - logo.height - margin

            canvas.paste(logo, (lx, ly), logo)
            
        except Exception as e:
            print(f"Logo overlay failed: {e}")
            
        return canvas

    def make_banner_text(self, name: str, design: str) -> str:
        return f"{name} 6.30 D.No {design}"

    def load_font(self, pts: int) -> ImageFont.FreeTypeFont:
        """Load font with better error handling"""
        try:
            # Try primary font
            if os.path.exists(self.FONT_PATH):
                return ImageFont.truetype(
                    self.FONT_PATH,
                    pts,
                    layout_engine=ImageFont.LAYOUT_RAQM,
                    font_variation={"wght": 800, "ital": 1},
                )
        except Exception as e:
            print(f"Primary font failed: {e}")
            
        # Try without font variations
        try:
            if os.path.exists(self.FONT_PATH):
                return ImageFont.truetype(self.FONT_PATH, pts)
        except Exception as e:
            print(f"Primary font without variations failed: {e}")
            
        # Try fallback fonts
        for fallback in self.FALLBACK_FONTS:
            try:
                return ImageFont.truetype(fallback, pts)
            except Exception:
                continue
        
        print("⚠️ Using default font - all font files failed")
        return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """FIXED: Handle PIL bbox returning unexpected formats"""
        try:
            bbox = font.getbbox(txt)
            
            if not bbox or len(bbox) != 4:
                raise ValueError(f"Invalid bbox: {bbox}")
            
            # Fix tuple elements - handle nested tuples
            corrected_bbox = []
            for elem in bbox:
                if isinstance(elem, (tuple, list)):
                    # Extract first element if nested
                    corrected_bbox.append(int(elem[0]))
                else:
                    corrected_bbox.append(int(elem))
            
            x0, y0, x1, y1 = corrected_bbox
            
            width = x1 - x0
            height = y1 - y0
            
            return max(width, 0), max(height, 0)
            
        except Exception as e:
            print(f"text_wh error with '{txt}': {e}")
            # Fallback estimation
            estimated_width = len(txt) * (getattr(font, 'size', 20) * 0.6)
            estimated_height = getattr(font, 'size', 20) * 1.2
            return int(estimated_width), int(estimated_height)

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        """Find best font size with error handling"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):
            try:
                f = self.load_font(size)
                text_width, _ = self.text_wh(txt, f)
                if text_width <= max_w:
                    return f
            except Exception as e:
                print(f"Font sizing error at size {size}: {e}")
                continue
        
        # Return minimum size as fallback
        return self.load_font(self.MIN_FONT_SIZE)
