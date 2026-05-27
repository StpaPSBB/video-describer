"""Сервис работы с файлами."""
import contextlib
import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import UploadFile
import yt_dlp

class FileService:
    """Класс сервиса для работы с файлами."""
    def __init__(
        self,
        id: uuid.UUID,
        upload_file: UploadFile | None = None,
        video_url: str | None = None,
    ):
        """Конструктор."""
        source_name = upload_file.filename if upload_file and upload_file.filename else None
        safe_filename = Path(source_name or self._filename_from_url(video_url) or "video.mp4").name
        self.work_dir = f"temp/{id}_{safe_filename}"
        self.source_filename = f"temp/source/{id}_{safe_filename}"
        self.frames_dir = f"{self.work_dir}/frames"
        self.result_filename = f"temp/results/{id}_{safe_filename}_result.json"
        self.file = upload_file.file if upload_file else None
        self.video_url = video_url


    def save_source(self) -> None:
        """Сохраняет исходное видео из файла или ссылки."""
        os.makedirs("temp/source/", exist_ok=True)
        os.makedirs(self.frames_dir, exist_ok=True)
        os.makedirs("temp/results", exist_ok=True)

        if self.file:
            self.save_upload_file()
            return

        if self.video_url:
            self.download_video()
            return

        raise ValueError("Не передан файл или ссылка на видео")

    def save_upload_file(self) -> None:
        """Сохраняет исходный файл."""
        if not self.file:
            raise ValueError("Файл не передан")

        with open(self.source_filename, "wb") as f:
            content = self.file.read()
            f.write(content)

    def download_video(self) -> None:
        """Скачивает видео по ссылке."""
        if not self.video_url:
            raise ValueError("Ссылка на видео не передана")

        output_template = str(Path(self.source_filename).with_suffix(".%(ext)s"))
        options = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        with open(os.devnull, "w", encoding="utf-8") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                with yt_dlp.YoutubeDL(options) as downloader:
                    info = downloader.extract_info(self.video_url, download=True)
                    downloaded_path = Path(downloader.prepare_filename(info))

        if downloaded_path != Path(self.source_filename):
            if Path(self.source_filename).exists():
                Path(self.source_filename).unlink()
            downloaded_path.rename(self.source_filename)

    
    def clean_files(self) -> None:
        """Удаляет временные файлы."""
        if os.path.exists(self.source_filename):
            os.remove(self.source_filename)
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
        if os.path.exists(self.result_filename):
            os.remove(self.result_filename)

    @staticmethod
    def _filename_from_url(video_url: str | None) -> str | None:
        if not video_url:
            return None

        parsed = urlparse(video_url)
        name = Path(parsed.path).name
        return name if name and "." in name else "video.mp4"
