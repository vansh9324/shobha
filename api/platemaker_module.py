#!/usr/bin/env python3
import io
import os
import logging
from PIL import Image, ImageDraw, ImageFont

# Try to import rembg for local background removal
try:
    import rembg
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateMaker:
    def __init__(self):
        """Your exact original configuration with debug logging"""
        # ORIGINAL DIMENSIONS - exactly as your working version
        self.FRAME_W, self.FRAME_H = 5000, 4000
        # Match reference proportions: minimal side/bottom padding, compact heading gap
        self.SIDE_PAD = 10
        self.TOP_PAD = 20
        self.BOTTOM_PAD = 10
        self.BANNER_PAD_Y = 10
        self.HEADING_GAP = 14
        self.MAX_FONT_SIZE = 80
        self.MIN_FONT_SIZE = 17
        self.TEXT_COLOR = (0, 0, 0)
        
        # CORRECTED PATHS - with debugging
        # Resolve font path relative to this module directory if available
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_font = os.path.join(base_dir, "..", "font", "NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf")
        candidate_font2 = os.path.join(base_dir, "..", "fonts", "NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf")
        self.FONT_PATH = candidate_font if os.path.exists(candidate_font) else (
            candidate_font2 if os.path.exists(candidate_font2) else "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        )
        self.FALLBACK_FONTS = ("DejaVuSans-Bold.ttf", "arial.ttf")
        # Try static logo inside this app first
        candidate_logo = os.path.join(base_dir, "static", "Shobha Emboss.png")
        self.LOGO_PATH = candidate_logo if os.path.exists(candidate_logo) else "logo/Shobha Emboss.png"
        
        # Check if files exist
        self.font_available = os.path.exists(self.FONT_PATH)
        self.logo_available = os.path.exists(self.LOGO_PATH)
        
        logger.info(f"🔤 Font available: {self.font_available} at {self.FONT_PATH}")
        logger.info(f"🖼️ Logo available: {self.logo_available} at {self.LOGO_PATH}")
        logger.info(f"🎭 Local rembg available: {REMBG_AVAILABLE}")
        
        if not self.font_available:
            logger.warning(f"⚠️ Custom font not found, will use system fallback")
        if not self.logo_available:
            logger.warning(f"⚠️ Logo not found, will skip logo overlay")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """Your exact original processing method with debug logging"""
        
        if status_callback:
            status_callback("📤 Reading image...")

        # Read image data
        if hasattr(image_file, 'read'):
            img_bytes = image_file.read()
        else:
            img_bytes = image_file

        # FIXED: Always use catalog name (your original logic)
        name = catalog
        filename = image_file.name if hasattr(image_file, 'name') else 'uploaded_image'
        
        logger.info(f"🎯 Processing: {filename} with catalog: {name}")
        logger.info(f"🔍 Input image size: {len(img_bytes)} bytes")

        if status_callback:
            status_callback("🎭 Removing background...")

        # 1. Remove BG - use local rembg if available, otherwise skip
        try:
            if REMBG_AVAILABLE:
                fg = self.remove_bg_from_bytes(img_bytes)
                logger.info("✅ Background removal successful")
            else:
                # Fallback: load original image
                fg = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                logger.warning("⚠️ Using original image - no background removal")
        except Exception as e:
            logger.error(f"❌ Background removal failed: {e}")
            fg = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

        logger.info(f"🔍 After BG removal: {fg.width}x{fg.height}")

        # 2. Trim transparency
        fg = self.trim_transparent(fg)
        logger.info(f"🔍 After trim: {fg.width}x{fg.height}")

        if status_callback:
            status_callback("📏 Resizing image...")

        # 3. Downsize into fixed window (as a max), keep actual frame dynamic
        fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)
        logger.info(f"🔍 After resize: {fg.width}x{fg.height}")
        frame_w, frame_h = fg.width, fg.height

        if status_callback:
            status_callback("🏷️ Adding logo overlay...")

        # 4. Logo overlay with debugging
        fg_canvas = Image.new("RGBA", fg.size, (0, 0, 0, 0))
        fg_canvas.paste(fg, (0, 0), fg)
        
        try:
            fg_canvas = self.add_logo_overlay(
                fg_canvas,
                (0, 0),
                (fg.width, fg.height),
                size_ratio=0.14,   # slightly smaller than before
                opacity=0.22,      # a bit lighter
                margin=40,
            )
            logger.info("✅ Logo overlay applied")
        except Exception as e:
            logger.error(f"❌ Logo overlay failed: {e}")

        fg = fg_canvas

        if status_callback:
            status_callback("✏️ Creating banner...")

        # 5. Banner text with debugging
        banner_text = self.make_banner_text(name, design_number)
        logger.info(f"🔍 Banner text: '{banner_text}'")
        
        # Heading should span most of the saree width (≈ 92%)
        font = self.best_font(banner_text, int(fg.width * 0.92))
        tw, th = self.text_wh(banner_text, font)
        banner_h = th + 2 * self.BANNER_PAD_Y
        
        logger.info(f"🔍 Text size: {tw}x{th}, banner height: {banner_h}")

        if status_callback:
            status_callback("🎨 Composing final image...")

        # 6. Create final canvas with dynamic width/height (matches saree width tightly)
        canvas_w = frame_w + 2 * self.SIDE_PAD
        canvas_h = self.TOP_PAD + banner_h + self.HEADING_GAP + frame_h + self.BOTTOM_PAD
        cv = Image.new("RGB", (canvas_w, canvas_h), (251, 251, 251))
        draw = ImageDraw.Draw(cv)
        
        logger.info(f"🔍 Final canvas: {cv.width}x{cv.height}")

        # 7. Draw banner text centred to saree width
        bx = self.SIDE_PAD + (frame_w - tw) // 2
        by = self.TOP_PAD + (banner_h - th) // 2
        
        logger.info(f"🔍 Text position: ({bx}, {by})")
        
        try:
            draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)
            logger.info("✅ Banner text drawn")
        except Exception as e:
            logger.error(f"❌ Text drawing failed: {e}")

        # 8. Paste the saree onto canvas right below heading with a small gap
        sx = self.SIDE_PAD + (frame_w - fg.width) // 2
        sy = self.TOP_PAD + banner_h + self.HEADING_GAP
        
        logger.info(f"🔍 Image position: ({sx}, {sy})")
        
        cv.paste(fg, (sx, sy), fg)

        if status_callback:
            status_callback("✅ Image processing complete!")

        logger.info("✅ Processing completed successfully")
        return cv.convert("RGB")

    def remove_bg_from_bytes(self, img_bytes):
        """Your original remove_bg method"""
        if not REMBG_AVAILABLE:
            raise RuntimeError("rembg not available")
        out_bytes = rembg.remove(img_bytes)
        return Image.open(io.BytesIO(out_bytes)).convert("RGBA")

    def trim_transparent(self, img):
        """Your exact original method"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        return img.crop(bbox) if bbox else img

    def downsize(self, img, box_w, box_h):
        """Your exact original method"""
        if img.width <= box_w and img.height <= box_h:
            return img
        scale = min(box_w / img.width, box_h / img.height)
        return img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.Resampling.LANCZOS
        )

    def make_canvas(self, banner_h):
        """Your exact original method"""
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        return Image.new("RGB", (w, h), (251, 251, 251))

    def add_logo_overlay(self, canvas, fg_pos, fg_size, size_ratio=0.20, opacity=0.31, margin=100):
        """Your original logo overlay with debug logging"""
        if not self.logo_available:
            logger.warning("⚠️ Logo file not found - skipping overlay")
            return canvas
            
        try:
            # Load logo
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            logger.info(f"🔍 Logo loaded: {logo.width}x{logo.height}")
            
            # Resize logo
            target_w = int(fg_size[0] * size_ratio)
            scale = target_w / logo.width
            logo = logo.resize(
                (target_w, int(logo.height * scale)),
                Image.Resampling.LANCZOS
            )
            logger.info(f"🔍 Logo resized: {logo.width}x{logo.height}")

            # Apply opacity
            alpha = logo.split().point(lambda p: int(p * opacity))
            logo.putalpha(alpha)
            
            # Calculate position
            sx, sy = fg_pos
            fw, fh = fg_size
            lx = sx + fw - logo.width - margin
            ly = sy + fh - logo.height - margin
            
            logger.info(f"🔍 Logo position: ({lx}, {ly})")
            
            # Paste logo
            canvas.paste(logo, (lx, ly), logo)
            logger.info("✅ Logo pasted successfully")
            
        except Exception as e:
            logger.error(f"❌ Logo overlay error: {e}")
            
        return canvas

    def make_banner_text(self, name, design):
        """Your exact original banner format"""
        return f"{name} 6.30 D.No {design}"

    def load_font(self, pts):
        """Load variable italic font if available, fallback gracefully."""
        try:
            if self.font_available:
                try:
                    # Try variable font with italic axis if supported
                    font = ImageFont.truetype(
                        self.FONT_PATH,
                        pts,
                        layout_engine=getattr(ImageFont, "LAYOUT_RAQM", 0),
                        font_variation={"wght": 700, "ital": 1},
                    )
                except Exception:
                    font = ImageFont.truetype(self.FONT_PATH, pts)
                logger.debug(f"✅ Custom font loaded: {pts}pt")
                return font
        except Exception as e:
            logger.warning(f"⚠️ Custom font failed: {e}")
        
        # Try fallback fonts
        for fb in self.FALLBACK_FONTS:
            try:
                font = ImageFont.truetype(fb, pts)
                logger.debug(f"✅ Fallback font loaded: {fb} at {pts}pt")
                return font
            except Exception:
                continue
        
        logger.warning("⚠️ Using default font - all TrueType fonts failed")
        return ImageFont.load_default()

    def text_wh(self, txt, font):
        """Your exact original method with error handling"""
        try:
            bbox = font.getbbox(txt)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception as e:
            logger.warning(f"⚠️ Text measurement failed: {e}")
            # Fallback estimation
            return len(txt) * 12, 20

    def best_font(self, txt, max_w):
        """Your exact original auto-sizing font method"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):
            f = self.load_font(size)
            w, _ = self.text_wh(txt, f)
            if w <= max_w:
                logger.info(f"✅ Selected font size: {size}pt")
                return f
        
        logger.warning(f"⚠️ Using minimum font size: {self.MIN_FONT_SIZE}pt")
        return self.load_font(self.MIN_FONT_SIZE)