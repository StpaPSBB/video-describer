"""Эндпоинты обработки видео."""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.services.video_svc import VideoService
from app.services.file_svc import FileService
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
async def upload_video(background_tasks: BackgroundTasks,
                       file: UploadFile = File(...)) -> FileResponse:
    """Загрузка видео и получение текстового файла с результатом."""
    if not file:
        raise HTTPException(status_code=400, detail="Файл не загружен")

    unique_id = str(uuid.uuid4())
    try:
        file_service=FileService(id=unique_id, upload_file=file)
        file_service.save_upload_file()
        source_filename=file_service.source_filename
        frames_dir=file_service.frames_dir
        result_filename=file_service.result_filename

        with open(result_filename, "w", encoding="utf-8") as f:
            f.write("penis")

        background_tasks.add_task(file_service.clean_files)
        return FileResponse(
            path=result_filename,
            media_type="text/plain",
            filename=f"result_{file.filename}.txt"
        )

    except Exception as e:
        if 'file_service' in locals():
            file_service.clean_files()
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

