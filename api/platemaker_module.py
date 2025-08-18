#!/usr/bin/env python3
"""
Advanced Image Processing Module for Shobha Sarees Photo Maker
Handles background removal, image enhancement, branding, and professional formatting
"""

import os
import time
import logging
from io import BytesIO
from typing import Optional, Callable, Tuple, Dict, Any
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_FRAME_SIZE = (2400, 1800)  # Optimized for mobile viewing
DEFAULT_PADDING = {'side': 30, 'top': 30, 'bottom': 30, 'banner_y': 40}
FONT_SIZE_RANGE = {'min': 24, 'max': 120}
TEXT_COLOR = (0, 0, 0)  # Black text
LOGO_CONFIG = {'size_ratio': 0.15, 'opacity': 0.25, 'margin': 80}

# API Configuration
REMBG_TIMEOUT = 15  # seconds
MAX_API_RETRIES = 2
RETRY_DELAY = 1  # seconds

class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass

class PlateMaker:
    """
    Advanced image processor for saree catalog creation.
    
    Features:
    - AI-powered background removal with fallback
    - Smart image enhancement and optimization
    - Professional branding and logo overlay
    - Responsive text sizing and formatting
    - Comprehensive error handling and logging
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize PlateMaker with configuration.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        # Load configuration
        self.config = self._load_config(config or {})
        
        # Initialize dimensions and styling
        self.FRAME_W, self.FRAME_H = self.config.get('frame_size', DEFAULT_FRAME_SIZE)
        padding = self.config.get('padding', DEFAULT_PADDING)
        self.SIDE_PAD = padding['side']
        self.TOP_PAD = padding['top']
        self.BOTTOM_PAD = padding['bottom']
        self.BANNER_PAD_Y = padding['banner_y']
        
        # Font configuration
        font_range = self.config.get('font_size_range', FONT_SIZE_RANGE)
        self.MAX_FONT_SIZE = font_range['max']
        self.MIN_FONT_SIZE = font_range['min']
        self.TEXT_COLOR = self.config.get('text_color', TEXT_COLOR)
        
        # File paths
        self.FONT_PATH = self.config.get('font_path', "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf")
        self.LOGO_PATH = self.config.get('logo_path', "logo/Shobha Emboss.png")
        
        # API configuration
        self.REMBG_API_URL = os.getenv("REMBG_API_URL", "https://api.rembg.com/rmbg").strip()
        self.REMBG_API_KEY = os.getenv("REMBG_API_KEY", "").strip()
        
        # Performance tracking
        self.stats = {
            'images_processed': 0,
            'api_calls_successful': 0,
            'api_calls_failed': 0,
            'fallback_removals': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0
        }
        
        # Initialize and validate resources
        self._init_resources()
        logger.info("✅ PlateMaker initialized successfully")
    
    def _load_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load and validate configuration."""
        default_config = {
            'frame_size': DEFAULT_FRAME_SIZE,
            'padding': DEFAULT_PADDING,
            'font_size_range': FONT_SIZE_RANGE,
            'text_color': TEXT_COLOR,
            'logo_config': LOGO_CONFIG,
            'enable_enhancement': True,
            'enable_gradient_background': True,
            'compression_quality': 95
        }
        
        # Merge with provided config
        merged_config = {**default_config, **config}
        logger.debug(f"Configuration loaded: {merged_config}")
        return merged_config
    
    def _init_resources(self) -> None:
        """Initialize and validate fonts, logos, and API availability."""
        # Check font availability
        self.font_available = Path(self.FONT_PATH).exists()
        logger.info(f"🔤 Custom font available: {self.font_available} ({self.FONT_PATH})")
        
        # Check logo availability
        self.logo_available = Path(self.LOGO_PATH).exists()
        logger.info(f"🖼️ Logo available: {self.logo_available} ({self.LOGO_PATH})")
        
        # Check API availability
        self.api_available = bool(self.REMBG_API_KEY)
        logger.info(f"🔑 Background removal API available: {self.api_available}")
        
        # Test font loading
        try:
            test_font = self.load_font(24)
            logger.info(f"✅ Font system functional: {type(test_font).__name__}")
        except Exception as e:
            logger.warning(f"⚠️ Font system issue: {e}")
    
    def process_image(
        self, 
        image_file: BytesIO, 
        catalog: str, 
        design_number: str, 
        status_callback: Optional[Callable[[str], None]] = None
    ) -> Image.Image:
        """
        Main image processing pipeline.
        
        Args:
            image_file: Input image as BytesIO
            catalog: Catalog name for branding
            design_number: Design number for labeling
            status_callback: Optional callback for progress updates
            
        Returns:
            Processed image ready for upload
            
        Raises:
            ImageProcessingError: If processing fails
        """
        start_time = time.time()
        
        try:
            if status_callback:
                status_callback("📤 Reading image...")
            
            # Read and validate image data
            img_bytes = self._read_image_data(image_file)
            
            logger.info(f"🎯 Processing: {catalog} - {design_number}")
            
            # Step 1: Background removal
            if status_callback:
                status_callback("🎭 Removing background...")
            
            foreground_img = self._remove_background(img_bytes, status_callback)
            
            # Step 2: Image optimization
            if status_callback:
                status_callback("📐 Optimizing image...")
            
            foreground_img = self._optimize_image(foreground_img)
            
            # Step 3: Logo overlay
            if status_callback:
                status_callback("🏷️ Adding branding...")
            
            foreground_img = self._add_logo_overlay(foreground_img)
            
            # Step 4: Text banner creation
            if status_callback:
                status_callback("✏️ Creating banner...")
            
            banner_text = self.make_banner_text(catalog, design_number)
            font, text_dims = self._prepare_text(banner_text)
            
            # Step 5: Final composition
            if status_callback:
                status_callback("🎨 Final composition...")
            
            final_image = self._compose_final_image(
                foreground_img, 
                banner_text, 
                font, 
                text_dims
            )
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_stats(processing_time, success=True)
            
            if status_callback:
                status_callback("✅ Processing complete!")
            
            logger.info(
                f"✅ Successfully processed: {catalog} - {design_number} "
                f"({processing_time:.2f}s)"
            )
            
            return final_image
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_stats(processing_time, success=False)
            
            logger.error(f"❌ Processing failed: {e} ({processing_time:.2f}s)")
            raise ImageProcessingError(f"Image processing failed: {str(e)}")
    
    def _read_image_data(self, image_file: BytesIO) -> bytes:
        """Read and validate image data."""
        try:
            if hasattr(image_file, "read"):
                img_bytes = image_file.read()
            else:
                img_bytes = image_file
            
            if not img_bytes:
                raise ValueError("Empty image data")
            
            # Validate it's a valid image
            try:
                test_img = Image.open(BytesIO(img_bytes))
                test_img.verify()
            except Exception as e:
                raise ValueError(f"Invalid image format: {e}")
            
            return img_bytes
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to read image data: {e}")
    
    def _remove_background(
        self, 
        img_bytes: bytes, 
        status_callback: Optional[Callable[[str], None]] = None
    ) -> Image.Image:
        """Remove background with API and fallback methods."""
        try:
            if self.api_available:
                return self._remove_background_api(img_bytes)
            else:
                if status_callback:
                    status_callback("🎭 Using smart background removal...")
                return self._remove_background_fallback(img_bytes)
                
        except Exception as e:
            logger.warning(f"API background removal failed: {e}")
            if status_callback:
                status_callback("🎭 Using smart background removal...")
            return self._remove_background_fallback(img_bytes)
    
    def _remove_background_api(self, img_bytes: bytes) -> Image.Image:
        """Remove background using external API."""
        if not self.REMBG_API_KEY:
            raise RuntimeError("REMBG API key not configured")
        
        files = {"image": ("upload.jpg", img_bytes)}
        headers = {"x-api-key": self.REMBG_API_KEY}
        
        for attempt in range(MAX_API_RETRIES):
            try:
                response = requests.post(
                    self.REMBG_API_URL,
                    headers=headers,
                    files=files,
                    timeout=REMBG_TIMEOUT
                )
                
                if response.status_code == 200:
                    self.stats['api_calls_successful'] += 1
                    return Image.open(BytesIO(response.content)).convert("RGBA")
                elif response.status_code == 429:  # Rate limited
                    if attempt < MAX_API_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                logger.warning(
                    f"API returned {response.status_code}: {response.text[:200]}"
                )
                
            except requests.exceptions.Timeout:
                logger.warning(f"API timeout (attempt {attempt + 1}/{MAX_API_RETRIES})")
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"API request error: {e}")
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
        
        self.stats['api_calls_failed'] += 1
        raise RuntimeError("Background removal API failed after retries")
    
    def _remove_background_fallback(self, img_bytes: bytes) -> Image.Image:
        """Enhanced fallback background removal using multiple techniques."""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            
            # Method 1: Corner-based background detection
            result = self._remove_bg_corner_detection(img)
            
            # Method 2: If corner detection didn't work well, try edge-based
            if self._is_removal_poor(result):
                result = self._remove_bg_edge_detection(img)
            
            self.stats['fallback_removals'] += 1
            logger.info("✅ Fallback background removal completed")
            return result
            
        except Exception as e:
            logger.error(f"Fallback background removal failed: {e}")
            # Return original image as RGBA if all methods fail
            return Image.open(BytesIO(img_bytes)).convert("RGBA")
    
    def _remove_bg_corner_detection(self, img: Image.Image) -> Image.Image:
        """Remove background using corner pixel analysis."""
        width, height = img.size
        
        # Sample corner pixels
        corner_samples = [
            img.getpixel((0, 0)),
            img.getpixel((width-1, 0)),
            img.getpixel((0, height-1)),
            img.getpixel((width-1, height-1))
        ]
        
        # Add edge samples for better detection
        edge_samples = [
            img.getpixel((width//2, 0)),  # Top center
            img.getpixel((0, height//2)),  # Left center
            img.getpixel((width-1, height//2)),  # Right center
            img.getpixel((width//2, height-1))  # Bottom center
        ]
        
        all_samples = corner_samples + edge_samples
        
        # Find most common background color
        from collections import Counter
        color_counts = Counter(all_samples)
        bg_color = color_counts.most_common(1)[0][0]
        
        # Remove background with adaptive tolerance
        return self._remove_color_with_tolerance(img, bg_color, tolerance=35)
    
    def _remove_bg_edge_detection(self, img: Image.Image) -> Image.Image:
        """Remove background using edge detection."""
        # Convert to numpy for processing
        img_array = np.array(img)
        
        # Use Pillow's built-in edge detection
        gray_img = img.convert('L')
        edges = gray_img.filter(ImageFilter.FIND_EDGES)
        
        # Create mask based on edge strength
        edge_array = np.array(edges)
        mask = edge_array > 30  # Threshold for edge detection
        
        # Apply morphological operations to fill gaps
        from scipy import ndimage
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_dilation(mask, iterations=2)
        
        # Apply mask to original image
        result = img.copy()
        result_array = np.array(result)
        result_array[:, :, 3] = mask * 255  # Set alpha channel
        
        return Image.fromarray(result_array, 'RGBA')
    
    def _remove_color_with_tolerance(
        self, 
        img: Image.Image, 
        bg_color: Tuple[int, int, int, int], 
        tolerance: int = 30
    ) -> Image.Image:
        """Remove specific color with tolerance."""
        data = img.getdata()
        new_data = []
        
        for pixel in data:
            # Calculate color difference
            if len(pixel) >= 3 and len(bg_color) >= 3:
                diff = sum(abs(pixel[i] - bg_color[i]) for i in range(3))
                
                if diff < tolerance:
                    # Make transparent
                    new_data.append((255, 255, 255, 0))
                else:
                    # Keep original pixel
                    new_data.append(pixel)
            else:
                new_data.append(pixel)
        
        result = img.copy()
        result.putdata(new_data)
        return result
    
    def _is_removal_poor(self, img: Image.Image, threshold: float = 0.8) -> bool:
        """Check if background removal was poor (too much transparency)."""
        if img.mode != 'RGBA':
            return False
        
        # Count transparent pixels
        data = img.getdata()
        transparent_count = sum(1 for pixel in data if pixel[3] == 0)
        total_pixels = len(data)
        
        transparency_ratio = transparent_count / total_pixels
        return transparency_ratio > threshold
    
    def _optimize_image(self, img: Image.Image) -> Image.Image:
        """Optimize image with trimming, resizing, and enhancement."""
        # Trim transparent areas
        img = self._trim_transparent(img)
        
        # Resize to fit frame
        img = self._smart_resize(img, self.FRAME_W, self.FRAME_H)
        
        # Apply enhancements if enabled
        if self.config.get('enable_enhancement', True):
            img = self._enhance_image(img)
        
        return img
    
    def _trim_transparent(self, img: Image.Image) -> Image.Image:
        """Trim transparent areas with smart padding."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        bbox = img.getbbox()
        if not bbox:
            return img
        
        # Add smart padding based on image size
        padding = max(5, min(img.width, img.height) // 100)
        x0, y0, x1, y1 = bbox
        
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(img.width, x1 + padding)
        y1 = min(img.height, y1 + padding)
        
        return img.crop((x0, y0, x1, y1))
    
    def _smart_resize(self, img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        """Smart resizing with aspect ratio preservation."""
        if img.width <= max_w and img.height <= max_h:
            return img
        
        # Calculate optimal scale
        scale = min(max_w / img.width, max_h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        
        # Use high-quality resampling
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """Apply subtle image enhancements."""
        try:
            # Slight sharpening
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # Slight contrast boost
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.05)
            
            # Very slight color saturation boost
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.02)
            
            return img
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return img
    
    def _add_logo_overlay(self, img: Image.Image) -> Image.Image:
        """Add logo overlay with proper positioning."""
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
        canvas.paste(img, (0, 0), img)
        
        if not self.logo_available:
            return canvas
        
        try:
            logo_config = self.config.get('logo_config', LOGO_CONFIG)
            
            logo = Image.open(self.LOGO_PATH).convert("RGBA")
            
            # Scale logo
            target_w = int(img.width * logo_config['size_ratio'])
            scale = target_w / logo.width
            logo = logo.resize(
                (target_w, int(logo.height * scale)), 
                Image.Resampling.LANCZOS
            )
            
            # Apply opacity
            if logo.mode == "RGBA":
                alpha = logo.split()[3].point(
                    lambda p: int(p * logo_config['opacity'])
                )
                logo.putalpha(alpha)
            
            # Position logo (bottom-right with margin)
            margin = logo_config['margin']
            lx = img.width - logo.width - margin
            ly = img.height - logo.height - margin
            
            # Ensure logo stays within bounds
            lx = max(10, min(lx, img.width - logo.width - 10))
            ly = max(10, min(ly, img.height - logo.height - 10))
            
            canvas.paste(logo, (lx, ly), logo)
            
        except Exception as e:
            logger.warning(f"Logo overlay failed: {e}")
        
        return canvas
    
    def _prepare_text(self, text: str) -> Tuple[ImageFont.FreeTypeFont, Tuple[int, int]]:
        """Prepare text with optimal font and get dimensions."""
        font = self._get_optimal_font(text, self.FRAME_W - 2 * self.SIDE_PAD)
        text_width, text_height = self._get_text_dimensions(text, font)
        return font, (text_width, text_height)
    
    def _compose_final_image(
        self, 
        foreground_img: Image.Image,
        banner_text: str,
        font: ImageFont.FreeTypeFont,
        text_dims: Tuple[int, int]
    ) -> Image.Image:
        """Compose the final image with background, text, and foreground."""
        text_width, text_height = text_dims
        banner_height = text_height + 2 * self.BANNER_PAD_Y
        
        # Create canvas
        canvas = self._create_canvas(banner_height)
        draw = ImageDraw.Draw(canvas)
        
        # Add text with shadow for better readability
        text_x = self.SIDE_PAD + (self.FRAME_W - text_width) // 2
        text_y = self.TOP_PAD + (banner_height - text_height) // 2
        
        # Text shadow
        shadow_offset = 2
        draw.text(
            (text_x + shadow_offset, text_y + shadow_offset),
            banner_text,
            font=font,
            fill=(128, 128, 128, 128)
        )
        
        # Main text
        draw.text((text_x, text_y), banner_text, font=font, fill=self.TEXT_COLOR)
        
        # Position and paste foreground image
        img_x = self.SIDE_PAD + (self.FRAME_W - foreground_img.width) // 2
        img_y = self.TOP_PAD + banner_height + (self.FRAME_H - foreground_img.height) // 2
        
        canvas.paste(foreground_img, (img_x, img_y), foreground_img)
        
        return canvas.convert("RGB")
    
    def _create_canvas(self, banner_height: int) -> Image.Image:
        """Create canvas with optional gradient background."""
        width = self.FRAME_W + 2 * self.SIDE_PAD
        height = self.TOP_PAD + banner_height + self.FRAME_H + self.BOTTOM_PAD
        
        canvas = Image.new("RGB", (width, height), "white")
        
        # Add subtle gradient if enabled
        if self.config.get('enable_gradient_background', True):
            try:
                gradient_height = 80
                gradient = Image.new("RGB", (width, gradient_height), "white")
                
                for y in range(gradient_height):
                    gray_value = 255 - int(y * 0.08)  # Subtle gradient
                    color = (gray_value, gray_value, gray_value)
                    for x in range(width):
                        gradient.putpixel((x, y), color)
                
                canvas.paste(gradient, (0, 0))
            except Exception as e:
                logger.warning(f"Gradient creation failed: {e}")
        
        return canvas
    
    def make_banner_text(self, catalog: str, design: str) -> str:
        """Create formatted banner text."""
        return f"{catalog.upper()} • 6.30 • D.No {design}"
    
    def load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load font with comprehensive fallback system."""
        font_paths = []
        
        # Add custom font if available
        if self.font_available:
            font_paths.append(self.FONT_PATH)
        
        # System font fallbacks (cross-platform)
        font_paths.extend([
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            # Windows
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            # Generic names
            "arial.ttf", "Arial.ttf", "calibri.ttf", "helvetica.ttf"
        ])
        
        # Try each font path
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except Exception:
                continue
        
        # Final fallback to default font
        logger.warning("Using default font - all TrueType fonts failed")
        return ImageFont.load_default()
    
    def _get_text_dimensions(self, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Get text dimensions with robust error handling."""
        try:
            bbox = font.getbbox(text)
            
            if not bbox or len(bbox) != 4:
                raise ValueError("Invalid bounding box")
            
            # Handle potential nested tuples (PIL version compatibility)
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
            logger.warning(f"Text dimension calculation failed: {e}")
            # Fallback estimation
            font_size = getattr(font, 'size', 20)
            estimated_width = int(len(text) * font_size * 0.6)
            estimated_height = int(font_size * 1.2)
            return estimated_width, estimated_height
    
    def _get_optimal_font(self, text: str, max_width: int) -> ImageFont.FreeTypeFont:
        """Find optimal font size that fits within max_width."""
        # Use binary search for efficiency
        min_size = self.MIN_FONT_SIZE
        max_size = self.MAX_FONT_SIZE
        best_font = self.load_font(min_size)
        
        while min_size <= max_size:
            mid_size = (min_size + max_size) // 2
            
            try:
                font = self.load_font(mid_size)
                text_width, _ = self._get_text_dimensions(text, font)
                
                if text_width <= max_width - 40:  # Leave margin
                    best_font = font
                    min_size = mid_size + 1
                else:
                    max_size = mid_size - 1
                    
            except Exception as e:
                logger.warning(f"Font sizing error at {mid_size}pt: {e}")
                max_size = mid_size - 1
        
        return best_font
    
    def _update_stats(self, processing_time: float, success: bool) -> None:
        """Update processing statistics."""
        self.stats['images_processed'] += 1
        self.stats['total_processing_time'] += processing_time
        
        # Update running average
        self.stats['average_processing_time'] = (
            self.stats['total_processing_time'] / self.stats['images_processed']
        )
        
        if not success:
            logger.warning("Processing failed - stats updated")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        api_total = self.stats['api_calls_successful'] + self.stats['api_calls_failed']
        api_success_rate = 0.0
        if api_total > 0:
            api_success_rate = (self.stats['api_calls_successful'] / api_total) * 100
        
        return {
            **self.stats,
            'api_success_rate_percent': round(api_success_rate, 2),
            'resources_available': {
                'custom_font': self.font_available,
                'logo': self.logo_available,
                'api': self.api_available
            }
        }
    
    def test_resources(self) -> Dict[str, Any]:
        """Test all resources and return status report."""
        results = {
            'font_system': 'unknown',
            'logo_loading': 'unknown',
            'api_connectivity': 'unknown',
            'overall_status': 'unknown'
        }
        
        # Test font system
        try:
            test_font = self.load_font(24)
            test_text = "Test Text"
            self._get_text_dimensions(test_text, test_font)
            results['font_system'] = 'working'
        except Exception as e:
            results['font_system'] = f'failed: {e}'
        
        # Test logo loading
        if self.logo_available:
            try:
                logo = Image.open(self.LOGO_PATH)
                logo.verify()
                results['logo_loading'] = 'working'
            except Exception as e:
                results['logo_loading'] = f'failed: {e}'
        else:
            results['logo_loading'] = 'file_not_found'
        
        # Test API connectivity
        if self.api_available:
            try:
                # Create a small test image
                test_img = Image.new('RGB', (100, 100), 'white')
                test_bytes = BytesIO()
                test_img.save(test_bytes, format='JPEG')
                test_bytes.seek(0)
                
                # Try API call with very short timeout
                response = requests.post(
                    self.REMBG_API_URL,
                    headers={"x-api-key": self.REMBG_API_KEY},
                    files={"image": ("test.jpg", test_bytes.getvalue())},
                    timeout=5
                )
                
                if response.status_code in [200, 400, 429]:  # Any reasonable response
                    results['api_connectivity'] = 'working'
                else:
                    results['api_connectivity'] = f'http_{response.status_code}'
                    
            except Exception as e:
                results['api_connectivity'] = f'failed: {e}'
        else:
            results['api_connectivity'] = 'no_api_key'
        
        # Overall status
        working_count = sum(1 for v in results.values() if v == 'working')
        if working_count >= 2:
            results['overall_status'] = 'functional'
        elif working_count >= 1:
            results['overall_status'] = 'limited'
        else:
            results['overall_status'] = 'impaired'
        
        return results
    
    def __del__(self):
        """Cleanup and log final statistics."""
        if hasattr(self, 'stats') and self.stats['images_processed'] > 0:
            stats = self.get_stats()
            logger.info(f"📊 PlateMaker session stats: {stats}")
