import io
import json
import os
import secrets
import sys
from datetime import timedelta, datetime
from dotenv import load_dotenv
import traceback
import logging

load_dotenv()

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("shobha")

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Also try loading .env files relative to this module for local dev
try:
    from pathlib import Path
    for candidate in [
        Path(BASE_DIR) / ".env",
        Path(BASE_DIR).parent / ".env",
        Path(BASE_DIR).parent.parent / ".env",
    ]:
        if candidate.exists():
            load_dotenv(dotenv_path=str(candidate), override=False)
except Exception:
    pass

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
SESSION_COOKIE_NAME = "admin_session"
SESSION_MAX_AGE_MIN = int(os.getenv("SESSION_MAX_AGE_MIN", "120"))

# File upload limits
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB per file
MAX_TOTAL_SIZE = 15 * 1024 * 1024  # 15MB total

# ---------------- FASTAPI ----------------
app = FastAPI(
    title="Shobha Sarees Photo Maker",
    description="Professional photo processing for saree catalogs",
    version="2.0.0"
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie=SESSION_COOKIE_NAME,
    same_site="lax",
    https_only=False,
    max_age=SESSION_MAX_AGE_MIN * 60,
)

# ---------------- GLOBAL SERVICES (LAZY INITIALIZED) ----------------
_platemaker = None
_drive_uploader = None
_temp_downloads: dict[str, dict] = {}

# Temp download storage limits
TEMP_MAX_ITEMS = 100
TEMP_TTL_SECONDS = 60 * 15  # 15 minutes

def get_platemaker():
    global _platemaker
    if _platemaker is None:
        try:
            # Try multiple import strategies to support different run modes
            try:
                from shobha.api.platemaker_module import PlateMaker  # type: ignore
            except Exception:
                try:
                    from .platemaker_module import PlateMaker  # type: ignore
                except Exception:
                    # Fallback to same-directory import
                    sys.path.append(BASE_DIR)
                    from platemaker_module import PlateMaker  # type: ignore
            _platemaker = PlateMaker()
            print("✅ PlateMaker initialized successfully")
        except Exception as e:
            print(f"❌ PlateMaker initialization failed: {e}")
            traceback.print_exc()
            _platemaker = False
    return _platemaker if _platemaker is not False else None

def get_drive_uploader():
    global _drive_uploader
    if _drive_uploader is None:
        try:
            # Try multiple import strategies to support different run modes
            try:
                from shobha.api.google_drive_uploader import DriveUploader  # type: ignore
            except Exception:
                try:
                    from .google_drive_uploader import DriveUploader  # type: ignore
                except Exception:
                    sys.path.append(BASE_DIR)
                    from google_drive_uploader import DriveUploader  # type: ignore
            _drive_uploader = DriveUploader()
            print("✅ DriveUploader initialized successfully")
        except Exception as e:
            print(f"❌ DriveUploader initialization failed: {e}")
            traceback.print_exc()
            _drive_uploader = False
    return _drive_uploader if _drive_uploader is not False else None

def _cleanup_temp_downloads():
    now = datetime.utcnow().timestamp()
    # Remove expired
    expired_keys = [k for k, v in _temp_downloads.items() if now - v.get("ts", 0) > TEMP_TTL_SECONDS]
    for k in expired_keys:
        _temp_downloads.pop(k, None)
    # Trim oldest if over capacity
    if len(_temp_downloads) > TEMP_MAX_ITEMS:
        for k in sorted(_temp_downloads.keys(), key=lambda x: _temp_downloads[x].get("ts", 0))[: len(_temp_downloads) - TEMP_MAX_ITEMS]:
            _temp_downloads.pop(k, None)

def _store_temp_download(data: bytes, filename: str) -> str:
    import uuid
    token = uuid.uuid4().hex
    _temp_downloads[token] = {"data": data, "filename": filename, "ts": datetime.utcnow().timestamp()}
    _cleanup_temp_downloads()
    return token

# ---------------- DATA ----------------
catalog_options = [
    "Blueberry", "Lavanya", "Soundarya",
    "Malai Crape", "Sweet Sixteen", 
    "Heritage", "Shakuntala"
]

# ------------- HELPERS -------------
def is_authenticated(request: Request) -> bool:
    return request.session.get("auth") is True

def login_user(request: Request):
    request.session["auth"] = True
    request.session["last_seen"] = datetime.utcnow().isoformat()
    request.session["login_time"] = datetime.utcnow().isoformat()

def logout_user(request: Request):
    request.session.clear()

def touch_session(request: Request) -> bool:
    if not request.session.get("auth"):
        return False
    
    last = request.session.get("last_seen")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if datetime.utcnow() - last_dt > timedelta(minutes=SESSION_MAX_AGE_MIN):
                request.session.clear()
                return False
        except Exception:
            request.session.clear()
            return False
    
    request.session["last_seen"] = datetime.utcnow().isoformat()
    return True

def validate_file_upload(files: list[UploadFile]) -> tuple[bool, str]:
    """Validate uploaded files"""
    if not files or len(files) == 0:
        return False, "No files uploaded"
    
    if len(files) > 10:
        return False, "Maximum 10 files allowed per upload"
    
    total_size = 0
    oversized_files = []
    invalid_files = []
    
    for file in files:
        if not file.content_type or not file.content_type.startswith('image/'):
            invalid_files.append(file.filename)
            continue
            
        file_size = file.size or 0
        if file_size > MAX_FILE_SIZE:
            oversized_files.append(f"{file.filename} ({file_size/1024/1024:.1f}MB)")
        
        total_size += file_size
    
    if invalid_files:
        return False, f"Invalid file types: {', '.join(invalid_files)}"
    
    if oversized_files:
        return False, f"Files too large (max 4MB): {', '.join(oversized_files)}"
    
    if total_size > MAX_TOTAL_SIZE:
        return False, f"Total size too large: {total_size/1024/1024:.1f}MB (max 15MB)"
    
    return True, "Valid"

# ------------- ROUTES: AUTH -------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    expects_json = "application/json" in (request.headers.get("accept") or "").lower()
    
    if not (username == ADMIN_USERNAME and password == ADMIN_PASSWORD):
        error_msg = "Invalid username or password"
        if expects_json:
            return JSONResponse({"ok": False, "error": error_msg}, status_code=401)
        return templates.TemplateResponse("login.html", {"request": request, "error": error_msg}, status_code=401)

    login_user(request)
    if expects_json:
        return JSONResponse({"ok": True, "message": "Login successful"})
    return RedirectResponse(url="/", status_code=303)

@app.post("/logout")
async def logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/login", status_code=303)

# ------------- ROUTES: PAGES -------------
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    if not touch_session(request):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/app", response_class=HTMLResponse)
async def app_view(request: Request):
    if not touch_session(request):
        return RedirectResponse(url="/login", status_code=303)
    
    # Get service status for frontend
    platemaker = get_platemaker()
    drive_uploader = get_drive_uploader()
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "catalogs": catalog_options,
        "services": {
            "platemaker_ready": platemaker is not None,
            "drive_uploader_ready": drive_uploader is not None
        }
    })

@app.get("/favicon.ico")
async def favicon():
    # Serve existing brand logo as favicon to avoid template 404s
    return RedirectResponse(url="/static/logo.png", status_code=307)

@app.get("/download/{token}")
async def download(token: str):
    item = _temp_downloads.get(token)
    if not item:
        raise HTTPException(status_code=404, detail="File expired or not found")
    # Optionally cleanup on access
    return Response(content=item["data"], media_type="image/jpeg", headers={
        "Content-Disposition": f"attachment; filename=\"{item['filename']}\""
    })

# ------------- API ENDPOINTS -------------
@app.get("/debug")
async def debug_info(request: Request):
    platemaker = get_platemaker()
    drive_uploader = get_drive_uploader()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "session": {
            "auth": request.session.get("auth", False),
            "last_seen": request.session.get("last_seen", "none"),
            "login_time": request.session.get("login_time", "none")
        },
        "services": {
            "platemaker_ready": platemaker is not None,
            "drive_uploader_ready": drive_uploader is not None,
        },
        "limits": {
            "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
            "max_total_size_mb": MAX_TOTAL_SIZE / 1024 / 1024,
            "max_files": 10
        },
        "env_vars": {
            "admin_username": bool(ADMIN_USERNAME),
            "session_secret": bool(SESSION_SECRET),
            "rembg_url": bool(os.getenv("REMBG_API_URL")),
            "rembg_key": bool(os.getenv("REMBG_API_KEY")),
            "google_creds": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            "google_refresh": bool(os.getenv("GOOGLE_REFRESH_TOKEN")),
        }
    }

@app.get("/health")
async def health_check():
    platemaker = get_platemaker()
    drive_uploader = get_drive_uploader()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "platemaker": platemaker is not None,
            "drive_uploader": drive_uploader is not None
        }
    }

@app.post("/upload", response_class=JSONResponse)
async def upload_images(
    request: Request,
    catalog: str = Form(...),
    mapping: str = Form(...),
    files: list[UploadFile] = File(...)
):
    # Check authentication
    if not touch_session(request):
        raise HTTPException(status_code=401, detail="Session expired")

    # Quick guard for serverless platforms (e.g., Vercel) to avoid network errors
    try:
        content_length = int((request.headers.get("content-length") or "0").strip())
    except ValueError:
        content_length = 0
    SAFE_TOTAL_LIMIT = MAX_TOTAL_SIZE + (2 * 1024 * 1024)  # allow ~2MB form overhead
    if content_length and content_length > SAFE_TOTAL_LIMIT:
        return JSONResponse({
            "error": f"Payload too large ({content_length/1024/1024:.1f}MB). Max {MAX_TOTAL_SIZE/1024/1024:.0f}MB total. Please compress or split uploads."
        }, status_code=413)

    logger.info(f"🔍 Received {len(files)} files")

    # Mobile-specific validation
    if len(files) > 10:
        return JSONResponse({"error": "Maximum 10 files allowed"}, status_code=413)
    
    # Check individual file sizes (mobile limit)
    # Note: file.size may be missing on some servers; enforce size during processing loop

    # Get services
    platemaker = get_platemaker()
    drive_uploader = get_drive_uploader()

    if platemaker is None:
        return JSONResponse({"error": "Image processing service unavailable"}, status_code=503)
    
    drive_available = drive_uploader is not None

    # Parse mapping
    try:
        design_map = {
            int(item["index"]): (item.get("design_number", "") or "").strip()
            for item in json.loads(mapping)
        }
    except Exception as e:
        return JSONResponse({"error": f"Invalid design mapping: {str(e)}"}, status_code=400)

    results = []
    total_bytes_seen = 0
    
    for idx, file in enumerate(files):
        try:
            img_bytes = await file.read()
            file_bytes_len = len(img_bytes)
            total_bytes_seen += file_bytes_len

            # Enforce per-file and total size limits server-side
            if file_bytes_len > MAX_FILE_SIZE:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": f"File too large ({file_bytes_len/1024/1024:.1f}MB). Max 4MB",
                })
                continue

            if total_bytes_seen > MAX_TOTAL_SIZE:
                return JSONResponse({
                    "error": f"Total size too large ({total_bytes_seen/1024/1024:.1f}MB). Max {MAX_TOTAL_SIZE/1024/1024:.0f}MB",
                    "results": results
                }, status_code=413)
            design_number = design_map.get(idx, "") or f"Design_{idx+1}"
            
            # Process image
            try:
                processed_img = platemaker.process_image(
                    io.BytesIO(img_bytes), 
                    catalog, 
                    design_number
                )
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": f"Processing failed: {str(e)[:100]}",
                    "design_number": design_number
                })
                continue

            # Upload to Drive
            output_filename = f"{catalog} - {design_number}.jpg"
            img_out_bytes = io.BytesIO()
            processed_img.save(img_out_bytes, format="JPEG", quality=95)
            img_out_bytes.seek(0)

            if drive_available:
                try:
                    url = drive_uploader.upload_image(img_out_bytes, output_filename, catalog)
                    results.append({
                        "filename": output_filename,
                        "url": url,
                        "status": "success",
                        "design_number": design_number
                    })
                except Exception as e:
                    results.append({
                        "filename": output_filename,
                        "status": "error",
                        "error": f"Upload failed: {str(e)[:100]}",
                        "design_number": design_number
                    })
            else:
                # Fallback: in-memory download link valid for a short time
                token = _store_temp_download(img_out_bytes.getvalue(), output_filename)
                temp_url = str(request.url_for("download", token=token))
                results.append({
                    "filename": output_filename,
                    "url": temp_url,
                    "status": "success",
                    "design_number": design_number,
                    "note": "Drive unavailable. Temporary download link valid for 15 minutes."
                })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": f"File error: {str(e)[:100]}"
            })

    return JSONResponse({
        "results": results,
        "catalog": catalog,
        "total": len(files),
        "successful": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"])
    })
# ------------- ERROR HANDLERS -------------
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def server_error(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
