# Video Describer

FastAPI-приложение для обработки видео через единый pipeline.

Программа принимает ссылку на видео или локальный видеофайл, сама скачивает/сохраняет источник, последовательно запускает обработку и возвращает JSON-отчет.

## Что делает pipeline

- `lab2` - извлекает кадры из видео.
- `lab3` - распознает текст на кадрах через EasyOCR.
- `lab4` - извлекает аудио и распознает речь через Whisper.
- `lab5` - ищет объекты на кадрах через YOLO.
- `lab6` - классифицирует кадры через ResNet.

## Установка

Из корня проекта:

```bash
cd /home/egoor/pukpuk/video-describer
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```
 Первая установка и первый запуск могут занять время.

## Запуск

```bash
cd /home/egoor/pukpuk/video-describer/backend
../.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

После запуска открыть:

```text
http://127.0.0.1:8000
```

## Использование

На странице можно:

- вставить ссылку на видео, например Rutube;
- или загрузить локальный видеофайл.

После обработки браузер скачает JSON-отчет.


## Результаты

Все созданные файлы сохраняются в корне проекта:

```text
temp/
```

Основные папки:

```text
temp/source/                 # скачанное или загруженное исходное видео
temp/results/                # итоговые JSON-отчеты
temp/<id>_video.mp4/frames/  # извлеченные кадры
temp/<id>_video.mp4/audio/   # аудио из видео
temp/<id>_video.mp4/renders/ # кадры с YOLO-разметкой
```

После успешной обработки файлы не удаляются автоматически.

## Формат отчета

JSON содержит:

- `report_type` - тип отчета;
- `source_info` - метаданные видео: имя файла, FPS, количество кадров, длительность;
- `labs` - подробный результат каждой лабораторной;
- `detections` - общий список найденных событий с кадрами и временем.

Пример структуры:

```json
{
  "report_type": "OPENCV_LABS_PIPELINE_REPORT",
  "source_info": {
    "filename": "video.mp4",
    "frameCount": 442,
    "fps": 29.333,
    "video_duration_formatted": "00:00:15",
    "analysis_timestamp": "2026-05-27T09:04:32"
  },
  "labs": {
    "lab2": {},
    "lab3": {},
    "lab4": {},
    "lab5": {},
    "lab6": {}
  },
  "detections": []
}
```

# степа лох(( ))лох степа