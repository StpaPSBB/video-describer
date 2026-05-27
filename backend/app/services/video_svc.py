"""Пайплайн обработки видео лабораторными работами 2-6."""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


class VideoService:
    """Запускает последовательную обработку загруженного видео."""

    def __init__(
        self,
        source_path: str | Path,
        work_dir: str | Path,
        result_path: str | Path,
        frame_step: int = 90,
        frame_limit: int = 30,
    ):
        self.source_path = Path(source_path)
        self.work_dir = Path(work_dir)
        self.result_path = Path(result_path)
        self.frames_dir = self.work_dir / "frames"
        self.processed_dir = self.work_dir / "processed_text"
        self.renders_dir = self.work_dir / "renders"
        self.audio_dir = self.work_dir / "audio"
        self.frame_step = frame_step
        self.frame_limit = frame_limit
        self.fps = 0.0

    def run_pipeline(self) -> Path:
        """Выполняет лабы 2-6 и сохраняет общий JSON-отчет."""
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = self._read_video_metadata()
        self.fps = metadata["fps"] or 0.0

        report: dict[str, Any] = {
            "report_type": "OPENCV_LABS_PIPELINE_REPORT",
            "source_info": {
                "filename": self.source_path.name,
                "frameCount": metadata["frame_count"],
                "fps": metadata["fps"],
                "video_duration_formatted": self._format_seconds(metadata["duration_seconds"]),
                "analysis_timestamp": datetime.now().isoformat(),
            },
            "labs": {},
            "detections": [],
        }

        frames = self._run_lab("lab2_extract_frames", self._extract_frames)
        report["labs"]["lab2"] = frames
        frame_paths = [Path(path) for path in frames.get("frames", [])]

        text_result = self._run_lab("lab3_text_ocr", self._recognize_text, frame_paths)
        report["labs"]["lab3"] = text_result
        report["detections"].extend(text_result.get("detections", []))

        audio_result = self._run_lab("lab4_audio_transcription", self._transcribe_audio)
        report["labs"]["lab4"] = audio_result
        report["detections"].extend(audio_result.get("detections", []))

        objects_result = self._run_lab("lab5_object_detection", self._detect_objects, frame_paths)
        report["labs"]["lab5"] = objects_result
        report["detections"].extend(objects_result.get("detections", []))

        classification_result = self._run_lab("lab6_frame_classification", self._classify_frames, frame_paths)
        report["labs"]["lab6"] = classification_result
        report["detections"].extend(classification_result.get("detections", []))

        self.result_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.result_path

    def _run_lab(self, name: str, func, *args) -> dict[str, Any]:
        try:
            result = func(*args)
            result.setdefault("status", "ok")
            return result
        except Exception as error:
            return {
                "status": "error",
                "name": name,
                "error": str(error),
            }

    def _read_video_metadata(self) -> dict[str, Any]:
        import cv2

        capture = cv2.VideoCapture(str(self.source_path))
        if not capture.isOpened():
            raise FileNotFoundError(f"video not found: {self.source_path}")

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        capture.release()
        duration_seconds = frame_count / fps if fps else 0
        return {
            "frame_count": frame_count,
            "fps": round(fps, 3),
            "duration_seconds": duration_seconds,
        }

    def _extract_frames(self) -> dict[str, Any]:
        import cv2

        if self.frame_step < 1:
            raise ValueError("frame_step must be greater than or equal to 1")

        if self.frames_dir.exists():
            shutil.rmtree(self.frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        capture = cv2.VideoCapture(str(self.source_path))
        if not capture.isOpened():
            raise FileNotFoundError(f"video not found: {self.source_path}")

        frame_paths: list[str] = []
        frame_index = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_index % self.frame_step == 0:
                frame_path = self.frames_dir / f"frame_{frame_index:06d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                frame_paths.append(str(frame_path))

                if len(frame_paths) >= self.frame_limit:
                    break

            frame_index += 1

        capture.release()
        return {
            "saved_frames": len(frame_paths),
            "step": self.frame_step,
            "limit": self.frame_limit,
            "frames": frame_paths,
        }

    def _recognize_text(self, frame_paths: list[Path]) -> dict[str, Any]:
        import cv2
        import easyocr
        import numpy as np

        if not frame_paths:
            raise FileNotFoundError("frames not found")

        if self.processed_dir.exists():
            shutil.rmtree(self.processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        with self._silence_output():
            reader = easyocr.Reader(["ru", "en"], gpu=False)

        raw_results: dict[str, str] = {}
        detections: list[dict[str, Any]] = []
        seen = set()

        for frame_path in frame_paths:
            image = cv2.imread(str(frame_path))
            if image is None:
                continue

            height, width = image.shape[:2]
            text_area = image[int(height * 0.65):height, 0:width]
            if text_area.size == 0:
                continue

            resized = cv2.resize(text_area, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            contrasted = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
            binary = cv2.adaptiveThreshold(
                contrasted,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                15,
                3,
            )
            denoised = cv2.medianBlur(binary, 3)
            processed = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
            cv2.imwrite(str(self.processed_dir / frame_path.name), processed)

            with self._silence_output():
                detected = reader.readtext(
                    processed,
                    detail=0,
                    paragraph=True,
                    text_threshold=0.5,
                    width_ths=0.7,
                    height_ths=0.7,
                )

            text = self._clean_text(" ".join(detected))
            if len(text) < 5 or text in seen:
                continue

            frame_number = self._frame_number(frame_path)
            raw_results[frame_path.name] = text
            seen.add(text)
            detections.append(
                self._time_detection(
                    frame_number,
                    frame_number,
                    subclass="text",
                    confidence=0.8,
                    detection_type="video_text",
                    extra={"text": text},
                )
            )

        return {
            "unique_phrases_count": len(detections),
            "unique_phrases": [item["text"] for item in detections],
            "results": raw_results,
            "detections": detections,
        }

    def _transcribe_audio(self) -> dict[str, Any]:
        import imageio_ffmpeg
        import whisper

        audio_path = self.audio_dir / "audio.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        self._prepare_ffmpeg_command(Path(ffmpeg))
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(self.source_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with self._silence_output():
                model = whisper.load_model("tiny")
                result = model.transcribe(str(audio_path), language="ru", verbose=False)

        detections = []
        for segment in result.get("segments", []):
            start_frame = self._seconds_to_frame(segment.get("start", 0))
            end_frame = self._seconds_to_frame(segment.get("end", 0))
            text = segment.get("text", "").strip()
            if text:
                detections.append(
                    self._time_detection(
                        start_frame,
                        end_frame,
                        subclass="speech",
                        confidence=0.98,
                        detection_type="audio",
                        extra={"text": text},
                    )
                )

        return {
            "audio_file": str(audio_path),
            "text": result.get("text", "").strip(),
            "segments_count": len(detections),
            "detections": detections,
        }

    def _prepare_ffmpeg_command(self, ffmpeg_path: Path) -> None:
        bin_dir = self.work_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        command_path = bin_dir / "ffmpeg"
        if command_path.exists() or command_path.is_symlink():
            command_path.unlink()
        command_path.symlink_to(ffmpeg_path)

        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    def _detect_objects(self, frame_paths: list[Path]) -> dict[str, Any]:
        import cv2
        from ultralytics import YOLO

        if not frame_paths:
            raise FileNotFoundError("frames not found")

        if self.renders_dir.exists():
            shutil.rmtree(self.renders_dir)
        self.renders_dir.mkdir(parents=True, exist_ok=True)

        with self._silence_output():
            model = YOLO("yolov8n.pt")

        detections_by_frame: dict[str, list[dict[str, Any]]] = {}
        detections: list[dict[str, Any]] = []

        for frame_path in frame_paths:
            image = cv2.imread(str(frame_path))
            if image is None:
                continue

            with self._silence_output():
                result = model(image, conf=0.25, verbose=False)[0]

            frame_objects = []
            frame_number = self._frame_number(frame_path)

            for box in result.boxes:
                class_id = int(box.cls[0])
                score = float(box.conf[0])
                name = model.names[class_id]
                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                frame_objects.append(
                    {
                        "class": name,
                        "confidence": round(score, 3),
                        "bbox": [x1, y1, x2, y2],
                    }
                )
                detections.append(
                    self._time_detection(
                        frame_number,
                        frame_number,
                        subclass=name,
                        confidence=round(score, 3),
                        detection_type="video_object",
                        extra={"bbox": [x1, y1, x2, y2]},
                    )
                )
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    image,
                    f"{name} {score:.2f}",
                    (x1, max(y1 - 8, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            if frame_objects:
                detections_by_frame[frame_path.name] = frame_objects
                cv2.imwrite(str(self.renders_dir / frame_path.name), image)

        return {
            "detected_frames": len(detections_by_frame),
            "objects_count": len(detections),
            "results": detections_by_frame,
            "detections": detections,
        }

    def _classify_frames(self, frame_paths: list[Path]) -> dict[str, Any]:
        import cv2
        import torch
        from PIL import Image
        from torchvision.models import ResNet50_Weights, resnet50

        if not frame_paths:
            raise FileNotFoundError("frames not found")

        weights = ResNet50_Weights.IMAGENET1K_V1
        preprocess = weights.transforms()
        categories = weights.meta["categories"]

        with self._silence_output():
            model = resnet50(weights=weights)
        model.eval()

        results = {}
        detections = []

        for frame_path in frame_paths:
            image = cv2.imread(str(frame_path))
            if image is None:
                continue

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            batch = preprocess(Image.fromarray(image)).unsqueeze(0)

            with torch.no_grad():
                probabilities = model(batch).squeeze(0).softmax(0)
                scores, class_ids = torch.topk(probabilities, 5)

            frame_result = [
                {
                    "class": categories[int(class_id)],
                    "score": round(float(score), 4),
                }
                for score, class_id in zip(scores, class_ids)
            ]
            results[frame_path.name] = frame_result

            if frame_result:
                top = frame_result[0]
                frame_number = self._frame_number(frame_path)
                detections.append(
                    self._time_detection(
                        frame_number,
                        frame_number,
                        subclass=top["class"],
                        confidence=top["score"],
                        detection_type="video_classification",
                        extra={"top5": frame_result},
                    )
                )

        summary = Counter(item[0]["class"] for item in results.values() if item)
        return {
            "classified_frames": len(results),
            "summary": dict(summary.most_common()),
            "results": results,
            "detections": detections,
        }

    def _time_detection(
        self,
        start_frame: int,
        end_frame: int,
        subclass: str,
        confidence: float,
        detection_type: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start_time = self._format_seconds(start_frame / self.fps if self.fps else 0)
        end_time = self._format_seconds(end_frame / self.fps if self.fps else 0)
        detection = {
            "startFrame": start_frame,
            "endFrame": end_frame,
            "start_time": start_time,
            "end_time": end_time,
            "time_interval": f"{start_time} - {end_time}",
            "subclass": subclass,
            "confidence": confidence,
            "type": detection_type,
        }
        if extra:
            detection.update(extra)
        return detection

    def _seconds_to_frame(self, seconds: float) -> int:
        return int(round(seconds * self.fps)) if self.fps else 0

    @staticmethod
    def _frame_number(frame_path: Path) -> int:
        match = re.search(r"frame_(\d+)", frame_path.stem)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"([a-zа-яё])([A-ZА-ЯЁ])", r"\1 \2", text)
        return text.strip("[]{}() ")

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        total = int(seconds)
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    @contextlib.contextmanager
    def _silence_output():
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                yield
