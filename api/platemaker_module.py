#!/usr/bin/env python3
import os
import time
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateMaker:
    def __init__(self):
        """Initialize with robust fallback mechanisms"""
        # Configuration
        self.FRAME_W, self.FRAME_H = 2400, 1800  # Optimized for mobile viewing
        self.SIDE_PAD = 30
        self.TOP_PAD = 30
        self.BOTTOM_PAD = 30
        self.BANNER_PAD_Y = 40
        self.MAX_FONT_SIZE = 120
        self.MIN_FONT_SIZE = 24
        self.TEXT_COLOR = (0, 0, 0)
        
        # File paths with fallbacks
        self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        self.LOGO_PATH = "logo/Shobha Emboss.png"
        
        # API configuration
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        # Initialize fonts and assets
        self._init_assets()
        
        logger.info("✅ PlateMaker initialized successfully")

    def _init_assets(self):
        """Initialize fonts and check asset availability"""
        # Check font availability
        self.font_available = os.path.exists(self.FONT_PATH)
        logger.info(f"🔤 Custom font available: {self.font_available}")
        
        # Check logo availability
        self.logo_available = os.path.exists(self.LOGO_PATH)
        logger.info(f"🖼️ Logo available: {self.logo_available}")
        
        # Check API availability
        self.api_available = bool(self.REMBG_API_KEY)
        logger.info(f"🔑 Background removal API: {self.api_available}")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """Main image processing pipeline with enhanced error handling"""
        try:
            if status_callback:
                status_callback("📤 Reading image...")

            # Read image data
            if hasattr(image_file, "read"):
                img_bytes = image_file.read()
            else:
                img_bytes = image_file

            logger.info(f"🎯 Processing: {catalog} - {design_number}")

            # Background removal with fallback
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

            # Image processing pipeline
            if status_callback:
                status_callback("📐 Optimizing image...")
            
            fg = self.trim_transparent(fg)
            fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)
            fg = self.enhance_image(fg)

            # Logo overlay
            if status_callback:
                status_callback("🏷️ Adding branding...")
            
            fg_canvas = Image.new("RGBA", fg.size, (0, 0, 0, 0))
            fg_canvas.paste(fg, (0, 0), fg)
            
            if self.logo_available:
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
            
            canvas = self.make_canvas(banner_h)
            draw = ImageDraw.Draw(canvas)

            # Center text
            bx = self.SIDE_PAD + (self.FRAME_W - tw) // 2
            by = self.TOP_PAD + (banner_h - th) // 2
            
            # Add text shadow for better readability
            shadow_offset = 2
            draw.text((bx + shadow_offset, by + shadow_offset), banner_text, 
                     font=font, fill=(128, 128, 128, 128))  # Shadow
            draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)

            # Center image
            sx = self.SIDE_PAD + (self.FRAME_W - fg_canvas.width) // 2
            sy = self.TOP_PAD + banner_h + (self.FRAME_H - fg_canvas.height) // 2
            canvas.paste(fg_canvas, (sx, sy), fg_canvas)

            if status_callback:
                status_callback("✅ Processing complete!")

            logger.info(f"✅ Successfully processed: {catalog} - {design_number}")
            return canvas.convert("RGB")

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise RuntimeError(f"Image processing failed: {str(e)}")

    def enhance_image(self, img: Image.Image) -> Image.Image:
        """Enhance image quality for better presentation"""
        try:
            # Slight sharpening
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # Slight contrast boost
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.05)
            
            return img
        except Exception:
            return img

    def remove_bg_from_bytes(self, img_bytes: bytes) -> Image.Image:
        """Remove background via API with timeout and retries"""
        if not self.REMBG_API_KEY:
            raise RuntimeError("API key not configured")

        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}

        for attempt in range(2):  # Only 2 attempts for faster fallback
            try:
                response = requests.post(
                    self.REMBG_API_URL, 
                    headers=headers, 
                    files=files, 
                    timeout=15  # Shorter timeout
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
        """Enhanced fallback background removal"""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            
            # Get corner pixels to determine background color
            width, height = img.size
            corners = [
                img.getpixel((0, 0)),
                img.getpixel((width-1, 0)),
                img.getpixel((0, height-1)),
                img.getpixel((width-1, height-1))
            ]
            
            # Find most common background color
            bg_color = max(set(corners), key=corners.count)
            
            # Remove background with tolerance
            data = img.getdata()
            new_data = []
            tolerance = 30
            
            for item in data:
                # Calculate color difference
                diff = sum(abs(item[i] - bg_color[i]) for i in range(3))
                
                if diff < tolerance:
                    new_data.append((255, 255, 255, 0))  # Transparent
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            logger.info("✅ Fallback background removal completed")
            return img
            
        except Exception as e:
            logger.warning(f"Fallback processing failed: {e}")
            # Return original image as RGBA
            return Image.open(BytesIO(img_bytes)).convert("RGBA")

    def trim_transparent(self, img: Image.Image) -> Image.Image:
        """Trim transparent areas with padding"""
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

    def downsize(self, img: Image.Image, box_w: int, box_h: int) -> Image.Image:
        """Smart resize with aspect ratio preservation"""
        if img.width <= box_w and img.height <= box_h:
            return img
        
        # Calculate scale to fit within bounds
        scale = min(box_w / img.width, box_h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def make_canvas(self, banner_h: int) -> Image.Image:
        """Create canvas with gradient background"""
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        
        # Create gradient background
        canvas = Image.new("RGB", (w, h), "white")
        
        # Optional: Add subtle gradient
        try:
            gradient = Image.new("RGB", (w, 50), "white")
            for y in range(50):
                gray_value = 255 - int(y * 0.1)
                color = (gray_value, gray_value, gray_value)
                for x in range(w):
                    gradient.putpixel((x, y), color)
            canvas.paste(gradient, (0, 0))
        except Exception:
            pass  # Fallback to plain white
        
        return canvas

    def add_logo_overlay(self, canvas: Image.Image, fg_pos, fg_size, size_ratio=0.15, opacity=0.25, margin=80) -> Image.Image:
        """Add logo with better positioning and effects"""
        try:
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            
            # Resize logo
            target_w = int(fg_size[0] * size_ratio)
            scale = target_w / logo.width
            logo = logo.resize((target_w, int(logo.height * scale)), Image.Resampling.LANCZOS)

            # Apply opacity
            if logo.mode == "RGBA":
                alpha = logo.split()[3].point(lambda p: int(p * opacity))
                logo.putalpha(alpha)

            # Position logo (bottom-right)
            sx, sy = fg_pos
            fw, fh = fg_size
            lx = sx + fw - logo.width - margin
            ly = sy + fh - logo.height - margin
            
            # Ensure logo stays within bounds
            lx = max(sx + 10, min(lx, sx + fw - logo.width - 10))
            ly = max(sy + 10, min(ly, sy + fh - logo.height - 10))

            canvas.paste(logo, (lx, ly), logo)
            
        except Exception as e:
            logger.warning(f"Logo overlay failed: {e}")
            
        return canvas

    def make_banner_text(self, name: str, design: str) -> str:
        """Create banner text with better formatting"""
        return f"{name.upper()} • 6.30 • D.No {design}"

    def load_font(self, pts: int) -> ImageFont.FreeTypeFont:
        """Load font with comprehensive fallbacks"""
        font_paths = []
        
        # Add custom font if available
        if self.font_available:
            font_paths.append(self.FONT_PATH)
        
        # System font fallbacks
        font_paths.extend([
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "arial.ttf", "Arial.ttf", "calibri.ttf"
        ])
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, pts)
            except Exception:
                continue
        
        # Final fallback
        logger.warning("Using default font - all TrueType fonts failed")
        return ImageFont.load_default()

    def text_wh(self, txt: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Get text dimensions with robust error handling"""
        try:
            bbox = font.getbbox(txt)
            
            if not bbox or len(bbox) != 4:
                raise ValueError("Invalid bbox")
            
            # Handle nested tuples in bbox (PIL version compatibility)
            fixed_bbox = []
            for elem in bbox:
                if isinstance(elem, (tuple, list)):
                    fixed_bbox.append(int(elem[0]))
                else:
                    fixed_bbox.append(int(elem))
            
            x0, y0, x1, y1 = fixed_bbox
            width = max(x1 - x0, 0)
            height = max(y1 - y0, 0)
            
            return width, height
            
        except Exception as e:
            logger.warning(f"text_wh failed: {e}")
            # Fallback estimation
            font_size = getattr(font, 'size', 20)
            estimated_width = len(txt) * int(font_size * 0.6)
            estimated_height = int(font_size * 1.2)
            return estimated_width, estimated_height

    def best_font(self, txt: str, max_w: int) -> ImageFont.FreeTypeFont:
        """Find optimal font size that fits within max_w"""
        # Start with larger steps for efficiency
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -8):
            try:
                font = self.load_font(size)
                text_width, _ = self.text_wh(txt, font)
                
                if text_width <= max_w - 40:  # Leave some margin
                    return font
                    
            except Exception as e:
                logger.warning(f"Font sizing error at {size}pt: {e}")
                continue
        
        # Fallback to minimum size
        return self.load_font(self.MIN_FONT_SIZE)
