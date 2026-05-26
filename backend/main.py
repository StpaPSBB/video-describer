"""Точка входа."""
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api.routers import video_rtr
import os

app = FastAPI()
app.include_router(video_rtr.router)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "templates", "index.html")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Отдает HTML интерфейс"""
    try:
        with open(frontend_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content=f"<h1>index.html not found at {frontend_path}</h1>",
            status_code=404
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)