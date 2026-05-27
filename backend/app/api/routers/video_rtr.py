"""Эндпоинты обработки видео."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.services.video_svc import VideoService
from app.services.file_svc import FileService
import uuid


router = APIRouter(
    prefix="/video",
    tags=["video"],
    responses={404: {"description": "Not found"}},
)


@router.post("/upload/")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    video_url: str | None = Form(None),
) -> FileResponse:
    """Загрузка видео и получение JSON-файла с результатом обработки."""
    if not file and not video_url:
        raise HTTPException(status_code=400, detail="Передайте файл или ссылку на видео")

    unique_id = str(uuid.uuid4())
    try:
        file_service = FileService(id=unique_id, upload_file=file, video_url=video_url)
        file_service.save_source()

        video_service = VideoService(
            source_path=file_service.source_filename,
            work_dir=file_service.work_dir,
            result_path=file_service.result_filename,
        )
        result_filename = video_service.run_pipeline()

        background_tasks.add_task(file_service.clean_files)
        result_download_name = file.filename if file and file.filename else "video_url"
        return FileResponse(
            path=result_filename,
            media_type="application/json",
            filename=f"result_{result_download_name}.json"
        )

    except Exception as e:
        if 'file_service' in locals():
            file_service.clean_files()
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
