#!/usr/bin/env python3
import os
import time
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont

class PlateMaker:
    def __init__(self):
        # Configuration
        self.FRAME_W, self.FRAME_H = 5_000, 4_000
        self.SIDE_PAD = 40
        self.TOP_PAD = 40
        self.BOTTOM_PAD = 40
        self.BANNER_PAD_Y = 60
        self.MAX_FONT_SIZE = 180
        self.MIN_FONT_SIZE = 40
        self.TEXT_COLOR = (0, 0, 0)
        
        # File paths - will check existence
        self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        self.LOGO_PATH = "logo/Shobha Emboss.png"
        
        # rembg API config
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        # Check file availability
        print(f"🔤 Font file exists: {os.path.exists(self.FONT_PATH)}")
        print(f"🖼️ Logo file exists: {os.path.exists(self.LOGO_PATH)}")
        print(f"🔑 REMBG API configured: {bool(self.REMBG_API_KEY)}")
        
        # Initialize successfully even if files missing
        print("✅ PlateMaker initialized with fallbacks")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        if status_callback:
            status_callback("📤 Reading image...")

        if hasattr(image_file, "read"):
            img_bytes = image_file.read()
        else:
            img_bytes = image_file

        name = catalog

        if status_callback:
            status_callback("🎭 Removing background...")

        # Background removal with fallback
        try:
            if self.REMBG_API_KEY:
                fg = self.remove_bg_from_bytes(img_bytes)
            else:
                raise RuntimeError("No API key - using fallback")
        except Exception as e:
            print(f"Background removal API failed: {e}")
            if status_callback:
                status_callback("🎭 Using simple background removal...")
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
            status_callback("✅ Complete!")

        return cv.convert("RGB")

    def remove_bg_from_bytes(self, img_bytes: bytes) -> Image.Image:
        if not self.REMBG_API_KEY:
            raise RuntimeError("REMBG API key not configured")

        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}

        for attempt in range(2):  # Reduced attempts for faster fallback
            try:
                resp = requests.post(self.REMBG_API_URL, headers=headers, files=files, timeout=20)
                if resp.status_code == 200:
                    return Image.open(BytesIO(resp.content)).convert("RGBA")
                print(f"rembg API error {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                print(f"rembg API attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    time.sleep(1)

        raise RuntimeError("Background removal API failed")

    def fallback_bg_removal(self, img_bytes: bytes) -> Image.Image:
        """Simple white background removal"""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            data = img.getdata()
            new_data = []
            
            for item in data:
                # Remove white/light backgrounds
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            return img
        except Exception:
            # Last resort - return original
            return Image.open(BytesIO(img_bytes)).convert("RGBA")

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
        """Add logo with fallback if file missing"""
        try:
            if not os.path.exists(self.LOGO_PATH):
                print("⚠️ Logo file missing - skipping overlay")
                return canvas
                
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            target_w = int(fg_size[0] * size_ratio)
            scale = target_w / logo.width
            logo = logo.resize((target_w, int(logo.height * scale)), Image.Resampling.LANCZOS)

            if logo.mode == "RGBA":
                alpha = logo.split()[3].point(lambda p: int(p * opacity))
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
        """Load font with comprehensive fallbacks"""
        # Try custom font if exists
        if os.path.exists(self.FONT_PATH):
            try:
                return ImageFont.truetype(self.FONT_PATH, pts)
            except Exception as e:
                print(f"Custom font failed: {e}")
        
        # Try system fonts
        system_fonts = [
            "arial.ttf", "Arial.ttf", "/System/Library/Fonts/Arial.ttf",
            "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "calibri.ttf", "Calibri.ttf"
        ]
        
        for font_path in system_fonts:
            try:
                return ImageFont.truetype(font_path, pts)
            except Exception:
                continue
        
        # Final fallback
        print("⚠️ Using default font - all TrueType fonts failed")
        return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Get text dimensions with error handling"""
        try:
            bbox = font.getbbox(txt)
            if not bbox or len(bbox) != 4:
                raise ValueError("Invalid bbox")
            
            # Handle nested tuples in bbox
            fixed_bbox = []
            for elem in bbox:
                if isinstance(elem, (tuple, list)):
                    fixed_bbox.append(int(elem[0]))
                else:
                    fixed_bbox.append(int(elem))
            
            x0, y0, x1, y1 = fixed_bbox
            return max(x1 - x0, 0), max(y1 - y0, 0)
            
        except Exception as e:
            print(f"text_wh failed: {e}")
            # Estimate based on font size
            font_size = getattr(font, 'size', 20)
            return int(len(txt) * font_size * 0.6), int(font_size * 1.2)

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        """Find optimal font size"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -5):  # Bigger steps
            try:
                f = self.load_font(size)
                text_width, _ = self.text_wh(txt, f)
                if text_width <= max_w:
                    return f
            except Exception as e:
                print(f"Font sizing error at {size}pt: {e}")
                continue
        
        return self.load_font(self.MIN_FONT_SIZE)
