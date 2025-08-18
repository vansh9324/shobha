#!/usr/bin/env python3
import os
import time
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateMaker:
    def __init__(self):
        """Initialize with ORIGINAL working dimensions and settings"""
        # RESTORED ORIGINAL SETTINGS - DO NOT CHANGE
        self.FRAME_W, self.FRAME_H = 5_000, 4_000  # Original dimensions that worked
        self.SIDE_PAD = 40  # Original padding
        self.TOP_PAD = 40
        self.BOTTOM_PAD = 40
        self.BANNER_PAD_Y = 60  # Original banner padding
        self.MAX_FONT_SIZE = 180  # Original font sizes
        self.MIN_FONT_SIZE = 40
        self.TEXT_COLOR = (0, 0, 0)  # Black text
        
        # File paths
        self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        self.LOGO_PATH = "logo/Shobha Emboss.png"
        
        # API configuration
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        # Check resources
        self.font_available = os.path.exists(self.FONT_PATH)
        self.logo_available = os.path.exists(self.LOGO_PATH)
        self.api_available = bool(self.REMBG_API_KEY)
        
        logger.info("✅ PlateMaker initialized with ORIGINAL settings")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """ORIGINAL processing logic - restored exactly as it was working"""
        try:
            if status_callback:
                status_callback("📤 Reading image...")

            # Read image data
            if hasattr(image_file, "read"):
                img_bytes = image_file.read()
            else:
                img_bytes = image_file

            logger.info(f"🎯 Processing: {catalog} - {design_number}")

            # Step 1: Background removal (keep mobile fixes but original fallback)
            if status_callback:
                status_callback("🎭 Removing background...")
            
            try:
                if self.api_available:
                    fg = self.remove_bg_from_bytes(img_bytes)
                else:
                    raise RuntimeError("API not configured - using fallback")
            except Exception as e:
                logger.warning(f"Background removal failed: {e}")
                if status_callback:
                    status_callback("🎭 Using fallback processing...")
                fg = self.fallback_bg_removal(img_bytes)

            # Step 2: ORIGINAL image processing pipeline
            if status_callback:
                status_callback("📐 Optimizing image...")
            
            fg = self.trim_transparent(fg)
            fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)  # Original dimensions
            
            # Step 3: Logo overlay (original positioning)
            if status_callback:
                status_callback("🏷️ Adding branding...")
            
            fg_canvas = Image.new("RGBA", fg.size, (0, 0, 0, 0))
            fg_canvas.paste(fg, (0, 0), fg)
            fg_canvas = self.add_logo_overlay(fg_canvas, (0, 0), (fg.width, fg.height))
            fg = fg_canvas

            # Step 4: ORIGINAL text processing
            if status_callback:
                status_callback("✏️ Creating banner...")
            
            banner_text = self.make_banner_text(catalog, design_number)
            font = self.best_font(banner_text, self.FRAME_W)
            tw, th = self.text_wh(banner_text, font)
            banner_h = th + 2 * self.BANNER_PAD_Y

            # Step 5: ORIGINAL final composition
            if status_callback:
                status_callback("🎨 Final composition...")
            
            cv = self.make_canvas(banner_h)
            draw = ImageDraw.Draw(cv)

            # ORIGINAL text positioning - centered
            bx = self.SIDE_PAD + (self.FRAME_W - tw) // 2
            by = self.TOP_PAD + (banner_h - th) // 2
            draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)

            # ORIGINAL image positioning - centered
            sx = self.SIDE_PAD + (self.FRAME_W - fg.width) // 2
            sy = self.TOP_PAD + banner_h + (self.FRAME_H - fg.height) // 2
            cv.paste(fg, (sx, sy), fg)

            if status_callback:
                status_callback("✅ Processing complete!")

            logger.info(f"✅ Successfully processed: {catalog} - {design_number}")
            return cv.convert("RGB")

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise RuntimeError(f"Image processing failed: {str(e)}")

    def remove_bg_from_bytes(self, img_bytes: bytes) -> Image.Image:
        """Mobile-optimized API call but original logic"""
        if not self.REMBG_API_KEY:
            raise RuntimeError("API key not configured")

        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}

        for attempt in range(2):  # Mobile: only 2 attempts
            try:
                response = requests.post(
                    self.REMBG_API_URL, 
                    headers=headers, 
                    files=files, 
                    timeout=15  # Mobile: shorter timeout
                )
                
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content)).convert("RGBA")
                elif response.status_code == 429:
                    if attempt == 0:
                        time.sleep(2)
                        continue
                
                logger.warning(f"API returned {response.status_code}: {response.text[:100]}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"API timeout (attempt {attempt + 1})")
                if attempt == 0:
                    time.sleep(1)

        raise RuntimeError("Background removal API failed")

    def fallback_bg_removal(self, img_bytes: bytes) -> Image.Image:
        """ORIGINAL fallback logic - simple white background removal"""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            data = img.getdata()
            new_data = []
            
            for item in data:
                # Simple white background removal (original logic)
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))  # Transparent
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            logger.info("✅ Fallback background removal completed")
            return img
            
        except Exception as e:
            logger.warning(f"Fallback processing failed: {e}")
            return Image.open(BytesIO(img_bytes)).convert("RGBA")

    def trim_transparent(self, img: Image.Image) -> Image.Image:
        """ORIGINAL trim logic"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        return img.crop(bbox) if bbox else img

    def downsize(self, img: Image.Image, box_w: int, box_h: int) -> Image.Image:
        """ORIGINAL downsize logic - do not change"""
        if img.width <= box_w and img.height <= box_h:
            return img
        scale = min(box_w / img.width, box_h / img.height)
        return img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)

    def make_canvas(self, banner_h: int) -> Image.Image:
        """ORIGINAL canvas creation - plain white background"""
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        return Image.new("RGB", (w, h), "white")  # Simple white background

    def add_logo_overlay(self, canvas: Image.Image, fg_pos, fg_size, size_ratio=0.20, opacity=0.31, margin=100) -> Image.Image:
        """ORIGINAL logo overlay logic"""
        try:
            if not self.logo_available:
                logger.warning("Logo file not found - skipping overlay")
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
            logger.warning(f"Logo overlay failed: {e}")
            
        return canvas

    def make_banner_text(self, name: str, design: str) -> str:
        """ORIGINAL banner text format"""
        return f"{name} 6.30 D.No {design}"

    def load_font(self, pts: int) -> ImageFont.FreeTypeFont:
        """ORIGINAL font loading with fallbacks"""
        try:
            if self.font_available:
                return ImageFont.truetype(self.FONT_PATH, pts, layout_engine=ImageFont.LAYOUT_RAQM)
        except Exception:
            pass
        
        # System font fallbacks
        system_fonts = [
            "arial.ttf", "Arial.ttf", "/System/Library/Fonts/Arial.ttf",
            "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "calibri.ttf", "Calibri.ttf"
        ]
        
        for font_path in system_fonts:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, pts)
            except Exception:
                continue
        
        logger.warning("Using default font - all TrueType fonts failed")
        return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """ORIGINAL text dimensions - fixed for PIL compatibility"""
        try:
            bbox = font.getbbox(txt)
            if not bbox or len(bbox) != 4:
                raise ValueError("Invalid bbox")
            
            # Handle potential nested tuples (PIL version compatibility)
            corrected_bbox = []
            for elem in bbox:
                if isinstance(elem, (tuple, list)):
                    corrected_bbox.append(int(elem[0]))
                else:
                    corrected_bbox.append(int(elem))
            
            x0, y0, x1, y1 = corrected_bbox
            width = x1 - x0
            height = y1 - y0
            
            return max(width, 0), max(height, 0)
            
        except Exception as e:
            logger.warning(f"text_wh failed: {e}")
            # Fallback estimation
            font_size = getattr(font, 'size', 20)
            estimated_width = len(txt) * int(font_size * 0.6)
            estimated_height = int(font_size * 1.2)
            return estimated_width, estimated_height

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        """ORIGINAL font sizing logic"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):  # Original step size
            try:
                f = self.load_font(size)
                text_width, _ = self.text_wh(txt, f)
                if text_width <= max_w:
                    return f
            except Exception as e:
                logger.warning(f"Font sizing error at size {size}: {e}")
                continue
        
        # Return minimum size as fallback
        return self.load_font(self.MIN_FONT_SIZE)
