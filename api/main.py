import io
import json
import os
import secrets
from datetime import timedelta, datetime

from dotenv import load_dotenv
load_dotenv()  # Load .env variables

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse

from platemaker_module import PlateMaker
from google_drive_uploader import DriveUploader

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this")

SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
SESSION_COOKIE_NAME = "admin_session"
SESSION_MAX_AGE_MIN = int(os.getenv("SESSION_MAX_AGE_MIN", "60"))

# ---------------- FASTAPI ----------------
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie=SESSION_COOKIE_NAME,
    same_site="lax",
    https_only=False,
    max_age=SESSION_MAX_AGE_MIN * 60,
)

platemaker = PlateMaker()
drive_uploader = DriveUploader()

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

def touch_session(request: Request):
    last = request.session.get("last_seen")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if datetime.utcnow() - last_dt > timedelta(minutes=SESSION_MAX_AGE_MIN):
                request.session.clear()
                return
        except Exception:
            pass
    request.session["last_seen"] = datetime.utcnow().isoformat()

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
    touch_session(request)
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/app", response_class=HTMLResponse)
async def app_view(request: Request):
    touch_session(request)
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "catalogs": catalog_options})

# ------------- ROUTES: API -------------
@app.post("/upload", response_class=JSONResponse)
async def upload_images(
    request: Request,
    catalog: str = Form(...),
    mapping: str = Form(...),
    files: list[UploadFile] = File(...)
):
    touch_session(request)
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        design_map = {
            int(item["index"]): (item.get("design_number", "") or "").strip()
            for item in json.loads(mapping)
        }
    except Exception:
        return JSONResponse({"error": "Invalid mapping payload"}, status_code=400)

    results = []
    for idx, file in enumerate(files):
        try:
            img_bytes = await file.read()
            design_number = design_map.get(idx, "") or f"Design_{idx+1}"

            processed_img = platemaker.process_image(
                io.BytesIO(img_bytes), catalog, design_number
            )

            output_filename = f"{catalog} - {design_number}.jpg"
            img_out_bytes = io.BytesIO()
            processed_img.save(img_out_bytes, format="JPEG", quality=100)
            img_out_bytes.seek(0)

            drive_url = drive_uploader.upload_image(
                img_out_bytes, output_filename, catalog
            )

            results.append({
                "filename": output_filename,
                "url": drive_url,
                "status": "success",
                "design_number": design_number
            })
        except Exception as e:
            results.append({
                "filename": getattr(file, "filename", f"image_{idx+1}"),
                "url": None,
                "status": "error",
                "error": str(e)
            })

    return JSONResponse({"results": results, "catalog": catalog})

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return PlainTextResponse("Not Found", status_code=404)

# This is important for Vercel
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
