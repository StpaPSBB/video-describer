"""Сервис работы с файлами."""
from fastapi import UploadFile
import uuid
import os
import shutil

class FileService:
    """Класс сервиса для работы с файлами."""
    def __init__(self, id: uuid.UUID, upload_file: UploadFile):
        """Конструктор."""
        self.source_filename = f"temp/source/{id}_{upload_file.filename}"
        self.frames_dir = f"temp/{id}_{upload_file.filename}/"
        self.result_filename = f"temp/results/{id}_{upload_file.filename}_result"
        self.file = upload_file.file


    def save_upload_file(self) -> None:
        """Сохраняет исходный файл."""
        os.makedirs("temp/source/", exist_ok=True)
        os.makedirs(self.frames_dir, exist_ok=True)
        os.makedirs("temp/results", exist_ok=True)

        with open(self.source_filename, "wb") as f:
            content = self.file.read()
            f.write(content)

    
    def clean_files(self) -> None:
        """Удаляет временные файлы."""
        if os.path.exists(self.source_filename):
            os.remove(self.source_filename)
        if os.path.exists(self.frames_dir):
            shutil.rmtree(self.frames_dir, ignore_errors=True)
        if os.path.exists(self.result_filename):
            os.remove(self.result_filename)