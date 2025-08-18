import io
import json
import os
import secrets
from datetime import timedelta, datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse

from api.platemaker_module import PlateMaker
from api.google_drive_uploader import DriveUploader

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
SESSION_COOKIE_NAME = "admin_session"
SESSION_MAX_AGE_MIN = int(os.getenv("SESSION_MAX_AGE_MIN", "60"))

# ---------------- GLOBAL STATE ----------------
platemaker = None
drive_uploader = None

# ---------------- LIFESPAN MANAGEMENT ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global platemaker, drive_uploader
    
    print("🚀 Starting application initialization...")
    
    # Initialize PlateMaker
    try:
        print("Initializing PlateMaker...")
        platemaker = PlateMaker()
        print("✅ PlateMaker ready")
    except Exception as e:
        print(f"❌ PlateMaker failed: {e}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        platemaker = None
    
    # Initialize DriveUploader
    try:
        print("Initializing DriveUploader...")
        drive_uploader = DriveUploader()
        print("✅ DriveUploader ready")
    except Exception as e:
        print(f"❌ DriveUploader failed: {e}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        drive_uploader = None
    
    # Summary
    services_ready = {
        "platemaker": platemaker is not None,
        "drive_uploader": drive_uploader is not None
    }
    
    print(f"🎯 Services status: {services_ready}")
    
    if not any(services_ready.values()):
        print("⚠️ No services initialized - app will have limited functionality")
    
    yield  # App runs here
    
    print("🧹 Application shutting down...")
    platemaker = None
    drive_uploader = None
# ---------------- FASTAPI APP ----------------
app = FastAPI(lifespan=lifespan)

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

def logout_user(request: Request):
    request.session.clear()

def touch_session(request: Request) -> bool:
    """Fixed session management"""
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

# ------------- ROUTES: AUTH -------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    expects_json = "application/json" in (request.headers.get("accept") or "").lower()
    
    if not (username == ADMIN_USERNAME and password == ADMIN_PASSWORD):
        if expects_json:
            return JSONResponse({"ok": False, "error": "Invalid credentials"}, status_code=401)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=401
        )

    login_user(request)
    if expects_json:
        return JSONResponse({"ok": True})
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
    return templates.TemplateResponse("index.html", {"request": request, "catalogs": catalog_options})

# ------------- DEBUG ENDPOINT -------------
@app.get("/debug")
async def debug_info(request: Request):
    return {
        "session": {
            "auth": request.session.get("auth", False),
            "last_seen": request.session.get("last_seen", "none")
        },
        "services": {
            "platemaker_ready": platemaker is not None,
            "drive_uploader_ready": drive_uploader is not None,
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

# ------------- ROUTES: API -------------
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

    # Check if services are initialized
    if platemaker is None:
        return JSONResponse(
            {"error": "Image processing service not available. Please try again later."}, 
            status_code=503
        )
    
    if drive_uploader is None:
        return JSONResponse(
            {"error": "File upload service not available. Please try again later."}, 
            status_code=503
        )

    # Parse mapping
    try:
        design_map = {
            int(item["index"]): (item.get("design_number", "") or "").strip()
            for item in json.loads(mapping)
        }
    except Exception as e:
        return JSONResponse({"error": f"Invalid mapping data: {str(e)}"}, status_code=400)

    results = []
    
    for idx, file in enumerate(files):
        try:
            img_bytes = await file.read()
            design_number = design_map.get(idx, "") or f"Design_{idx+1}"
            
            # Process image
            try:
                processed_img = platemaker.process_image(
                    io.BytesIO(img_bytes), catalog, design_number
                )
            except Exception as e:
                error_msg = "Image processing failed"
                if "rembg" in str(e).lower() or "background removal" in str(e).lower():
                    error_msg = "Background removal service unavailable"
                elif "timeout" in str(e).lower():
                    error_msg = "Processing timeout"
                
                results.append({
                    "filename": getattr(file, "filename", f"image_{idx+1}"),
                    "status": "error",
                    "error": f"{error_msg}. Please try again.",
                    "design_number": design_number
                })
                continue

            # Upload to Drive
            output_filename = f"{catalog} - {design_number}.jpg"
            img_out_bytes = io.BytesIO()
            processed_img.save(img_out_bytes, format="JPEG", quality=100)
            img_out_bytes.seek(0)

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

        except Exception as e:
            results.append({
                "filename": getattr(file, "filename", f"image_{idx+1}"),
                "status": "error",
                "error": f"File processing error: {str(e)[:100]}"
            })

    return JSONResponse({"results": results, "catalog": catalog})

# ------------- HEALTH CHECK -------------
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "services": {
            "platemaker": platemaker is not None,
            "drive_uploader": drive_uploader is not None
        }
    }

# ------------- ERRORS -------------
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return PlainTextResponse("Not Found", status_code=404)
