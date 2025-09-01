#!/usr/bin/env python3
import io
import os
import logging
import requests
import base64
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateMaker:
    def __init__(self):
        """Your exact original configuration with multiple HuggingFace API options"""
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
        
        logger.info(f"📤 Font available: {self.font_available} at {self.FONT_PATH}")
        logger.info(f"🖼️ Logo available: {self.logo_available} at {self.LOGO_PATH}")
        
        if not self.font_available:
            logger.warning(f"⚠️ Custom font not found, will use system fallback")
        if not self.logo_available:
            logger.warning(f"⚠️ Logo not found, will skip logo overlay")

    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """Your exact original processing method with improved HuggingFace API integration"""
        
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
        logger.info(f"📏 Input image size: {len(img_bytes)} bytes")

        if status_callback:
            status_callback("🎭 Removing background...")

        # 1. Remove BG using HuggingFace API with multiple endpoints
        try:
            fg = self.remove_bg_huggingface(img_bytes)
            logger.info("✅ Background removal successful")
        except Exception as e:
            logger.error(f"❌ Background removal failed: {e}")
            fg = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            logger.warning("⚠️ Using original image - no background removal")

        logger.info(f"📏 After BG removal: {fg.width}x{fg.height}")

        # 2. Trim transparency
        fg = self.trim_transparent(fg)
        logger.info(f"📏 After trim: {fg.width}x{fg.height}")

        if status_callback:
            status_callback("📏 Resizing image...")

        # 3. Downsize into fixed window (as a max), keep actual frame dynamic
        fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)
        logger.info(f"📏 After resize: {fg.width}x{fg.height}")
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
        logger.info(f"📝 Banner text: '{banner_text}'")
        
        # Heading should span most of the saree width (≈ 92%)
        font = self.best_font(banner_text, int(fg.width * 0.92))
        tw, th = self.text_wh(banner_text, font)
        banner_h = th + 2 * self.BANNER_PAD_Y
        
        logger.info(f"📝 Text size: {tw}x{th}, banner height: {banner_h}")

        if status_callback:
            status_callback("🎨 Composing final image...")

        # 6. Create final canvas with dynamic width/height (matches saree width tightly)
        canvas_w = frame_w + 2 * self.SIDE_PAD
        canvas_h = self.TOP_PAD + banner_h + self.HEADING_GAP + frame_h + self.BOTTOM_PAD
        cv = Image.new("RGB", (canvas_w, canvas_h), "white")
        draw = ImageDraw.Draw(cv)
        
        logger.info(f"📝 Final canvas: {cv.width}x{cv.height}")

        # 7. Draw banner text centred to saree width
        bx = self.SIDE_PAD + (frame_w - tw) // 2
        by = self.TOP_PAD + (banner_h - th) // 2
        
        logger.info(f"📝 Text position: ({bx}, {by})")
        
        try:
            draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)
            logger.info("✅ Banner text drawn")
        except Exception as e:
            logger.error(f"❌ Text drawing failed: {e}")

        # 8. Paste the saree onto canvas right below heading with a small gap
        sx = self.SIDE_PAD + (frame_w - fg.width) // 2
        sy = self.TOP_PAD + banner_h + self.HEADING_GAP
        
        logger.info(f"📝 Image position: ({sx}, {sy})")
        
        cv.paste(fg, (sx, sy), fg)

        if status_callback:
            status_callback("✅ Image processing complete!")

        logger.info("✅ Processing completed successfully")
        return cv.convert("RGB")

    def remove_bg_huggingface(self, img_bytes):
        """Multiple HuggingFace API endpoints for background removal"""
        
        # Get HuggingFace token from environment
        hf_token = os.getenv('HUGGINGFACE_API_KEY') or os.getenv('HF_TOKEN')
        headers = {}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
        
        # Try multiple API endpoints in order of preference
        endpoints = [
            # Option 1: HuggingFace Space API (most reliable)
            {
                "url": "https://briaai-bria-rmbg-1-4.hf.space/api/predict",
                "method": "space_api"
            },
            # Option 2: Alternative Space
            {
                "url": "https://not-lain-background-removal.hf.space/api/predict", 
                "method": "space_api"
            },
            # Option 3: Direct Inference API (if available)
            {
                "url": "https://api-inference.huggingface.co/models/briaai/RMBG-1.4",
                "method": "inference_api"
            }
        ]
        
        for i, endpoint in enumerate(endpoints):
            try:
                logger.info(f"🔄 Trying endpoint {i+1}: {endpoint['method']}")
                
                if endpoint["method"] == "space_api":
                    return self._try_space_api(endpoint["url"], img_bytes)
                elif endpoint["method"] == "inference_api":
                    return self._try_inference_api(endpoint["url"], img_bytes, headers)
                    
            except Exception as e:
                logger.warning(f"⚠️ Endpoint {i+1} failed: {e}")
                continue
        
        # All endpoints failed
        raise RuntimeError("All HuggingFace endpoints failed")
    
    def _try_space_api(self, api_url, img_bytes):
        """Try HuggingFace Space API with base64 encoding"""
        # Convert image to base64
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        data_url = f"data:image/png;base64,{img_b64}"
        
        payload = {"data": [data_url]}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result_data = response.json()
            if result_data.get('data') and len(result_data['data']) > 0:
                # Handle both base64 and direct URL responses
                result = result_data['data'][0]
                if isinstance(result, str):
                    if result.startswith('data:image'):
                        result_b64 = result.replace('data:image/png;base64,', '')
                        result_bytes = base64.b64decode(result_b64)
                    else:
                        # It might be a URL, try to download
                        img_response = requests.get(result)
                        result_bytes = img_response.content
                else:
                    raise RuntimeError("Unexpected response format from Space API")
                
                result_image = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
                logger.info(f"✅ Space API success: {result_image.width}x{result_image.height}")
                return result_image
            else:
                raise RuntimeError("No data in Space API response")
        else:
            raise RuntimeError(f"Space API error: {response.status_code} - {response.text}")
    
    def _try_inference_api(self, api_url, img_bytes, headers):
        """Try HuggingFace Inference API with direct image data"""
        response = requests.post(api_url, headers=headers, data=img_bytes, timeout=60)
        
        if response.status_code == 200:
            result_image = Image.open(io.BytesIO(response.content)).convert("RGBA")
            logger.info(f"✅ Inference API success: {result_image.width}x{result_image.height}")
            return result_image
        elif response.status_code == 503:
            # Model loading, wait and retry
            import time
            time.sleep(20)
            response = requests.post(api_url, headers=headers, data=img_bytes, timeout=60)
            if response.status_code == 200:
                result_image = Image.open(io.BytesIO(response.content)).convert("RGBA")
                logger.info(f"✅ Inference API success on retry: {result_image.width}x{result_image.height}")
                return result_image
        
        raise RuntimeError(f"Inference API error: {response.status_code} - {response.text}")

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

    def add_logo_overlay(self, canvas, fg_pos, fg_size, size_ratio=0.20, opacity=0.31, margin=100):
        """Your original logo overlay with debug logging"""
        if not self.logo_available:
            logger.warning("⚠️ Logo file not found - skipping overlay")
            return canvas
            
        try:
            # Load logo
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            logger.info(f"📝 Logo loaded: {logo.width}x{logo.height}")
            
            # Resize logo
            target_w = int(fg_size[0] * size_ratio)
            scale = target_w / logo.width
            logo = logo.resize(
                (target_w, int(logo.height * scale)),
                Image.Resampling.LANCZOS
            )
            logger.info(f"📝 Logo resized: {logo.width}x{logo.height}")

            # Apply opacity
            alpha = logo.getchannel('A')
            alpha = alpha.point(lambda p: int(p * opacity))
            logo.putalpha(alpha)
            
            # Calculate position
            sx, sy = fg_pos
            fw, fh = fg_size
            lx = sx + fw - logo.width - margin
            ly = sy + fh - logo.height - margin
            
            logger.info(f"📝 Logo position: ({lx}, {ly})")
            
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
        """FIXED: Your text measurement method with proper error handling"""
        try:
            bbox = font.getbbox(txt)
            # Ensure we return integers, not tuples
            width = bbox[2] - bbox
            height = bbox[13] - bbox[14]
            return int(width), int(height)
        except Exception as e:
            logger.warning(f"⚠️ Text measurement failed: {e}")
            # Better fallback estimation based on font size
            estimated_width = len(txt) * int(font.size * 0.6)
            estimated_height = int(font.size * 1.2)
            return estimated_width, estimated_height

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