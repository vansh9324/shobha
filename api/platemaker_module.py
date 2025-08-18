#!/usr/bin/env python3
import os
import time
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateMaker:
    def __init__(self):
        """Initialize with 4MB-optimized dimensions and correct file paths"""
        # SCALED DIMENSIONS - maintain exact proportions of Sweet Sixteen
        self.FRAME_W, self.FRAME_H = 3160, 2528  # 63% of 5000x4000
        self.SIDE_PAD = 25   # 63% of 40
        self.TOP_PAD = 25    # 63% of 40
        self.BOTTOM_PAD = 25 # 63% of 40
        self.BANNER_PAD_Y = 38  # 63% of 60
        self.MAX_FONT_SIZE = 114  # 63% of 180
        self.MIN_FONT_SIZE = 25   # 63% of 40
        self.TEXT_COLOR = (0, 0, 0)
        
        # CORRECTED FILE PATHS - from main root directory
        self.FONT_PATH = os.path.join(os.getcwd(), "fonts", "NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf")
        self.LOGO_PATH = os.path.join(os.getcwd(), "logo", "Shobha Emboss.png")
        
        # Alternative paths in case of deployment directory differences
        if not os.path.exists(self.FONT_PATH):
            self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        if not os.path.exists(self.LOGO_PATH):
            self.LOGO_PATH = "logo/Shobha Emboss.png"
        
        # API configuration
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        # Resource checks with detailed logging
        self.font_available = os.path.exists(self.FONT_PATH)
        self.logo_available = os.path.exists(self.LOGO_PATH)
        self.api_available = bool(self.REMBG_API_KEY)
        
        logger.info(f"🔤 Font path: {self.FONT_PATH} - Available: {self.font_available}")
        logger.info(f"🖼️ Logo path: {self.LOGO_PATH} - Available: {self.logo_available}")
        logger.info(f"🔑 API available: {self.api_available}")
        logger.info("✅ PlateMaker initialized with 4MB-optimized dimensions")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """Process with 4MB-optimized pipeline"""
        try:
            if status_callback:
                status_callback("📤 Reading image...")

            # Read image data
            if hasattr(image_file, "read"):
                img_bytes = image_file.read()
            else:
                img_bytes = image_file

            logger.info(f"🎯 Processing: {catalog} - {design_number}")

            # Background removal
            if status_callback:
                status_callback("🎭 Removing background...")
            
            try:
                if self.api_available:
                    fg = self.remove_bg_from_bytes(img_bytes)
                else:
                    raise RuntimeError("API not configured")
            except Exception as e:
                logger.warning(f"Background removal failed: {e}")
                if status_callback:
                    status_callback("🎭 Using fallback processing...")
                fg = self.fallback_bg_removal(img_bytes)

            # Image optimization
            if status_callback:
                status_callback("📐 Optimizing image...")
            
            fg = self.trim_transparent(fg)
            fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)

            # Logo overlay
            if status_callback:
                status_callback("🏷️ Adding branding...")
            
            fg_canvas = Image.new("RGBA", fg.size, (0, 0, 0, 0))
            fg_canvas.paste(fg, (0, 0), fg)
            fg_canvas = self.add_logo_overlay(fg_canvas, (0, 0), (fg.width, fg.height))

            # Text banner
            if status_callback:
                status_callback("✏️ Creating banner...")
            
            banner_text = self.make_banner_text(catalog, design_number)
            font = self.best_font(banner_text, self.FRAME_W)
            tw, th = self.text_wh(banner_text, font)
            banner_h = th + 2 * self.BANNER_PAD_Y

            # Final composition
            if status_callback:
                status_callback("🎨 Final composition...")
            
            cv = self.make_canvas(banner_h)
            draw = ImageDraw.Draw(cv)

            # Center text
            bx = self.SIDE_PAD + (self.FRAME_W - tw) // 2
            by = self.TOP_PAD + (banner_h - th) // 2
            draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)

            # Center image
            sx = self.SIDE_PAD + (self.FRAME_W - fg_canvas.width) // 2
            sy = self.TOP_PAD + banner_h + (self.FRAME_H - fg_canvas.height) // 2
            cv.paste(fg_canvas, (sx, sy), fg_canvas)

            if status_callback:
                status_callback("✅ Processing complete!")

            return cv.convert("RGB")

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise RuntimeError(f"Image processing failed: {str(e)}")

    def remove_bg_from_bytes(self, img_bytes: bytes) -> Image.Image:
        """API background removal with mobile timeout"""
        if not self.REMBG_API_KEY:
            raise RuntimeError("API key not configured")

        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}

        for attempt in range(2):
            try:
                response = requests.post(
                    self.REMBG_API_URL, 
                    headers=headers, 
                    files=files, 
                    timeout=15
                )
                
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content)).convert("RGBA")
                elif response.status_code == 429 and attempt == 0:
                    time.sleep(2)
                    continue
                
                logger.warning(f"API returned {response.status_code}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"API timeout (attempt {attempt + 1})")
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
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            return img
            
        except Exception:
            return Image.open(BytesIO(img_bytes)).convert("RGBA")

    def trim_transparent(self, img: Image.Image) -> Image.Image:
        """Remove transparent edges"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        return img.crop(bbox) if bbox else img

    def downsize(self, img: Image.Image, box_w: int, box_h: int) -> Image.Image:
        """Scale image to fit canvas while maintaining aspect ratio"""
        if img.width <= box_w and img.height <= box_h:
            return img
        scale = min(box_w / img.width, box_h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def make_canvas(self, banner_h: int) -> Image.Image:
        """Create white canvas"""
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        return Image.new("RGB", (w, h), "white")

    def add_logo_overlay(self, canvas: Image.Image, fg_pos, fg_size, size_ratio=0.20, opacity=0.31, margin=63) -> Image.Image:
        """Add logo overlay with correct path"""
        try:
            if not self.logo_available:
                logger.warning("Logo file not available - skipping overlay")
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
            logger.info("✅ Logo overlay applied successfully")
            
        except Exception as e:
            logger.warning(f"Logo overlay failed: {e}")
            
        return canvas

    def make_banner_text(self, name: str, design: str) -> str:
        """Original banner format"""
        return f"{name} 6.30 D.No {design}"

    def load_font(self, pts: int) -> ImageFont.FreeTypeFont:
        """Load font with correct path and system fallbacks"""
        # Try custom font first
        try:
            if self.font_available:
                font = ImageFont.truetype(self.FONT_PATH, pts)
                logger.debug(f"Loaded custom font at {pts}pt")
                return font
        except Exception as e:
            logger.warning(f"Custom font loading failed: {e}")
        
        # System font fallbacks
        system_fonts = [
            "arial.ttf", 
            "Arial.ttf", 
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf"
        ]
        
        for font_path in system_fonts:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, pts)
                    logger.debug(f"Loaded system font: {font_path} at {pts}pt")
                    return font
            except Exception:
                continue
        
        logger.warning("All TrueType fonts failed, using default font")
        return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Get text dimensions"""
        try:
            bbox = font.getbbox(txt)
            if bbox and len(bbox) == 4:
                x0, y0, x1, y1 = bbox
                return max(x1 - x0, 0), max(y1 - y0, 0)
        except Exception as e:
            logger.warning(f"Text dimension calculation failed: {e}")
        
        # Fallback estimation
        font_size = getattr(font, 'size', 20)
        return len(txt) * int(font_size * 0.6), int(font_size * 1.2)

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        """Find optimal font size for text width"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):
            try:
                font = self.load_font(size)
                text_width, _ = self.text_wh(txt, font)
                if text_width <= max_w:
                    logger.debug(f"Selected font size: {size}pt for text width: {text_width}px")
                    return font
            except Exception as e:
                logger.warning(f"Font sizing error at {size}pt: {e}")
                continue
        
        logger.warning(f"Using minimum font size: {self.MIN_FONT_SIZE}pt")
        return self.load_font(self.MIN_FONT_SIZE)
