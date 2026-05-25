from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from settings import UPLOAD_DIR, RESULTS_DIR
from services.video_svc import VideoService
from datetime import date
import os
import uuid
from pathlib import Path

router = APIRouter(
    prefix="/video",
    tags=["video"],
    responses={404: {"description": "Not found"}},
)


@router.post("/upload/")
async def upload_video(file: UploadFile = File(...)) -> FileResponse:
    """Загрузка видео и получение текстового файла с результатом."""
    if not file:
        raise HTTPException(status_code=400, detail="Файл не загружен")
    
    unique_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    result_path = RESULTS_DIR / f"{unique_id}_result.txt"

    video_service = VideoService(upload_dir=UPLOAD_DIR, results_dir=RESULTS_DIR, uuid=unique_id)
    
    video_service.do_some_shit()

    return FileResponse(
        path=result_path,
        media_type="text/plain",
        filename=f"result_{file.filename}.txt"
    )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
    
    finally:
        # Очищаем временные файлы
        if video_path.exists():
            os.remove(video_path)
        if result_path.exists():
            os.remove(result_path)