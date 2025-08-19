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
        """Proportionally scaled dimensions for compressed 2500x2000 input"""
        
        # TARGET INPUT: 2500x2000 (5:4 ratio) compressed images
        self.FRAME_W, self.FRAME_H = 4000, 3200  # Larger than before
        self.SIDE_PAD = 35
        self.TOP_PAD = 35
        self.BOTTOM_PAD = 35
        self.BANNER_PAD_Y = 50
        self.MAX_FONT_SIZE = 120
        self.MIN_FONT_SIZE = 30
        self.TEXT_COLOR = (0, 0, 0)
        
        # Correct file paths
        self.FONT_PATH = os.path.join(os.getcwd(), "fonts", "NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf")
        self.LOGO_PATH = os.path.join(os.getcwd(), "logo", "Shobha Emboss.png")
        
        # Fallback paths
        if not os.path.exists(self.FONT_PATH):
            self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        if not os.path.exists(self.LOGO_PATH):
            self.LOGO_PATH = "logo/Shobha Emboss.png"
        
        # API configuration
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        # Resource checks
        self.font_available = os.path.exists(self.FONT_PATH)
        self.logo_available = os.path.exists(self.LOGO_PATH)
        self.api_available = bool(self.REMBG_API_KEY)
        
        logger.info(f"✅ PlateMaker optimized for quality compression: {self.FRAME_W}x{self.FRAME_H}")
        logger.info(f"📏 Font range: {self.MIN_FONT_SIZE}-{self.MAX_FONT_SIZE}pt")
        logger.info(f"🔤 Font available: {self.font_available}")
        logger.info(f"🖼️ Logo available: {self.logo_available}")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """Process with proportionally scaled pipeline"""
        try:
            if status_callback:
                status_callback("📤 Reading image...")

            # Read compressed image data
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
            fg = self.smart_resize(fg, self.FRAME_W, self.FRAME_H)

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

            # Final composition with calculated canvas
            if status_callback:
                status_callback("🎨 Final composition...")
            
            cv = self.make_canvas(banner_h)
            draw = ImageDraw.Draw(cv)

            # Center text (proportional positioning)
            bx = self.SIDE_PAD + (self.FRAME_W - tw) // 2
            by = self.TOP_PAD + (banner_h - th) // 2
            draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)

            # Center image (proportional positioning)
            sx = self.SIDE_PAD + (self.FRAME_W - fg_canvas.width) // 2
            sy = self.TOP_PAD + banner_h + (self.FRAME_H - fg_canvas.height) // 2
            cv.paste(fg_canvas, (sx, sy), fg_canvas)

            if status_callback:
                status_callback("✅ Processing complete!")

            logger.info(f"✅ Successfully processed: {catalog} - {design_number}")
            logger.info(f"📏 Final canvas size: {cv.width}x{cv.height}")
            
            return cv.convert("RGB")

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise RuntimeError(f"Image processing failed: {str(e)}")

    def remove_bg_from_bytes(self, img_bytes: bytes) -> Image.Image:
        """API background removal optimized for mobile"""
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
        """Enhanced fallback background removal"""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            
            # Get corner samples for background color detection
            w, h = img.size
            corners = [
                img.getpixel((0, 0)),
                img.getpixel((w-1, 0)),
                img.getpixel((0, h-1)),
                img.getpixel((w-1, h-1))
            ]
            
            # Most common corner color as background
            from collections import Counter
            bg_color = Counter(corners).most_common(1)[0][0]
            
            data = img.getdata()
            new_data = []
            tolerance = 35
            
            for pixel in data:
                if len(pixel) >= 3 and len(bg_color) >= 3:
                    diff = sum(abs(pixel[i] - bg_color[i]) for i in range(3))
                    if diff < tolerance:
                        new_data.append((255, 255, 255, 0))  # Transparent
                    else:
                        new_data.append(pixel)
                else:
                    new_data.append(pixel)
            
            img.putdata(new_data)
            logger.info("✅ Fallback background removal completed")
            return img
            
        except Exception as e:
            logger.warning(f"Fallback processing failed: {e}")
            return Image.open(BytesIO(img_bytes)).convert("RGBA")

    def trim_transparent(self, img: Image.Image) -> Image.Image:
        """Remove transparent edges with small padding"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        bbox = img.getbbox()
        if not bbox:
            return img
            
        # Add small padding
        padding = 5
        x0, y0, x1, y1 = bbox
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(img.width, x1 + padding)
        y1 = min(img.height, y1 + padding)
        
        return img.crop((x0, y0, x1, y1))

    def smart_resize(self, img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        """High-quality proportional resize"""
        if img.width <= max_w and img.height <= max_h:
            return img
        
        # Maintain aspect ratio
        scale = min(max_w / img.width, max_h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        
        # Use highest quality resampling
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def make_canvas(self, banner_h: int) -> Image.Image:
        """Create canvas sized for content + padding"""
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        return Image.new("RGB", (w, h), "white")

    def add_logo_overlay(self, canvas: Image.Image, fg_pos, fg_size, size_ratio=0.20, opacity=0.31, margin=50) -> Image.Image:
        """Add proportionally scaled logo overlay"""
        try:
            if not self.logo_available:
                logger.warning("Logo file not available")
                return canvas
                
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            target_w = int(fg_size[0] * size_ratio)
            scale = target_w / logo.width
            logo = logo.resize((target_w, int(logo.height * scale)), Image.Resampling.LANCZOS)

            if logo.mode == "RGBA":
                alpha = logo.split().point(lambda p: int(p * opacity))
                logo.putalpha(alpha)

            # Position bottom-right with proportional margin
            sx, sy = fg_pos
            fw, fh = fg_size
            lx = sx + fw - logo.width - margin
            ly = sy + fh - logo.height - margin
            
            # Ensure within bounds
            lx = max(sx + 10, min(lx, sx + fw - logo.width - 10))
            ly = max(sy + 10, min(ly, sy + fh - logo.height - 10))
            
            canvas.paste(logo, (lx, ly), logo)
            logger.info("✅ Logo overlay applied")
            
        except Exception as e:
            logger.warning(f"Logo overlay failed: {e}")
            
        return canvas

    def make_banner_text(self, name: str, design: str) -> str:
        """Standard banner format"""
        return f"{name} 6.30 D.No {design}"

    def load_font(self, pts: int) -> ImageFont.FreeTypeFont:
        """Load font with fallbacks"""
        try:
            if self.font_available:
                return ImageFont.truetype(self.FONT_PATH, pts)
        except Exception:
            pass
        
        # System font fallbacks
        system_fonts = [
            "arial.ttf", "Arial.ttf", 
            "/System/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arial.ttf"
        ]
        
        for font_path in system_fonts:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, pts)
            except Exception:
                continue
        
        return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Get text dimensions with fallback"""
        try:
            bbox = font.getbbox(txt)
            if bbox and len(bbox) == 4:
                x0, y0, x1, y1 = bbox
                return max(x1 - x0, 0), max(y1 - y0, 0)
        except Exception:
            pass
        
        # Fallback estimation
        font_size = getattr(font, 'size', 20)
        return len(txt) * int(font_size * 0.6), int(font_size * 1.2)

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        """Find optimal font size within proportional range"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):
            try:
                font = self.load_font(size)
                text_width, _ = self.text_wh(txt, font)
                if text_width <= max_w - (2 * self.SIDE_PAD):
                    logger.debug(f"Selected font size: {size}pt")
                    return font
            except Exception:
                continue
        
        return self.load_font(self.MIN_FONT_SIZE)
