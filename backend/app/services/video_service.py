import asyncio
import hashlib
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

from backend.app.core.config import get_settings

try:
    import ffmpeg
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    ffmpeg = None

SLIDE_SECONDS = 2.0
FADE_SECONDS = 0.35
VIDEO_SIZE = "1080x1080"
VIDEO_FPS = 30


class VideoGenerationError(Exception):
    pass


class VideoUploadError(Exception):
    pass


async def _generate_with_gemini(
    image_urls: list[str],
    product_idea: dict[str, Any],
    shop_style: str
) -> bytes | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    # Veo/Gemini access is intentionally not active in Phase 4. Keeping this
    # boundary makes it straightforward to enable later without touching API code.
    return None


async def _download_images(image_urls: list[str], directory: Path) -> list[Path]:
    image_paths: list[Path] = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for index, image_url in enumerate(image_urls):
            try:
                response = await client.get(image_url)
            except httpx.HTTPError as exc:
                raise VideoGenerationError("Could not download listing image") from exc
            if response.status_code >= 400 or not response.content:
                raise VideoGenerationError("Could not download listing image")

            image_path = directory / f"image_{index}.jpg"
            image_path.write_bytes(response.content)
            image_paths.append(image_path)
    return image_paths


def _image_stream(image_path: Path, seconds: float):
    if ffmpeg is None:
        raise VideoGenerationError("ffmpeg-python is not installed")

    frame_count = max(1, int(seconds * VIDEO_FPS))
    return (
        ffmpeg
        .input(str(image_path), loop=1, t=seconds)
        .filter("scale", 1200, 1200, force_original_aspect_ratio="increase")
        .filter("crop", 1080, 1080)
        .filter(
            "zoompan",
            z="min(zoom+0.0012,1.08)",
            d=frame_count,
            x="iw/2-(iw/zoom/2)",
            y="ih/2-(ih/zoom/2)",
            s=VIDEO_SIZE,
            fps=VIDEO_FPS
        )
        .filter("setsar", "1")
        .filter("format", "yuv420p")
    )


def _render_with_crossfade(image_paths: list[Path], output_path: Path) -> None:
    segment_seconds = SLIDE_SECONDS + FADE_SECONDS
    streams = [_image_stream(image_path, segment_seconds) for image_path in image_paths]
    stream = streams[0]
    for index, next_stream in enumerate(streams[1:], start=1):
        offset = max(0.1, (SLIDE_SECONDS - FADE_SECONDS) * index)
        stream = (
            ffmpeg
            .filter(
                [stream, next_stream],
                "xfade",
                transition="fade",
                duration=FADE_SECONDS,
                offset=offset
            )
            .filter("format", "yuv420p")
        )

    (
        ffmpeg
        .output(
            stream,
            str(output_path),
            vcodec="libx264",
            pix_fmt="yuv420p",
            r=VIDEO_FPS,
            movflags="+faststart"
        )
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )


def _render_segment(image_path: Path, output_path: Path) -> None:
    stream = _image_stream(image_path, SLIDE_SECONDS)
    (
        ffmpeg
        .output(
            stream,
            str(output_path),
            vcodec="libx264",
            pix_fmt="yuv420p",
            r=VIDEO_FPS,
            movflags="+faststart"
        )
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )


def _render_with_concat(image_paths: list[Path], directory: Path, output_path: Path) -> None:
    segment_paths: list[Path] = []
    for index, image_path in enumerate(image_paths):
        segment_path = directory / f"segment_{index}.mp4"
        _render_segment(image_path, segment_path)
        segment_paths.append(segment_path)

    list_path = directory / "segments.txt"
    list_path.write_text(
        "\n".join(f"file '{segment_path.as_posix()}'" for segment_path in segment_paths),
        encoding="utf-8"
    )
    (
        ffmpeg
        .input(str(list_path), format="concat", safe=0)
        .output(str(output_path), c="copy", movflags="+faststart")
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )


def _render_slideshow(image_paths: list[Path], directory: Path) -> Path:
    if ffmpeg is None:
        raise VideoGenerationError("ffmpeg-python is not installed")
    if not image_paths:
        raise VideoGenerationError("No images available for video generation")

    output_path = directory / "listing-video.mp4"
    try:
        if len(image_paths) == 1:
            _render_segment(image_paths[0], output_path)
        else:
            _render_with_crossfade(image_paths, output_path)
    except (ffmpeg.Error, OSError) as exc:
        if len(image_paths) == 1:
            raise VideoGenerationError("ffmpeg video generation failed") from exc
        try:
            _render_with_concat(image_paths, directory, output_path)
        except (ffmpeg.Error, OSError) as fallback_exc:
            raise VideoGenerationError("ffmpeg video generation failed") from fallback_exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise VideoGenerationError("ffmpeg returned an empty video")
    return output_path


async def generate_listing_video(
    image_urls: list[str],
    product_idea: dict[str, Any],
    shop_style: str
) -> bytes:
    gemini_video = await _generate_with_gemini(image_urls, product_idea, shop_style)
    if gemini_video:
        return gemini_video

    with TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir)
        image_paths = await _download_images(image_urls, directory)
        output_path = await asyncio.to_thread(_render_slideshow, image_paths, directory)
        return output_path.read_bytes()


def _cloudinary_signature(params: dict[str, str], api_secret: str) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()


async def upload_video(video_bytes: bytes, listing_id: str) -> str:
    settings = get_settings()
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise VideoUploadError("Cloudinary is not configured")
    if not video_bytes:
        raise VideoUploadError("Video is empty")

    timestamp = str(int(time.time()))
    public_id = f"listifyai/listings/{listing_id}/video-{uuid.uuid4().hex}"
    params_to_sign = {"public_id": public_id, "timestamp": timestamp}
    signature = _cloudinary_signature(params_to_sign, settings.cloudinary_api_secret)
    upload_url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/video/upload"
    data = {
        "api_key": settings.cloudinary_api_key,
        "timestamp": timestamp,
        "public_id": public_id,
        "signature": signature
    }
    files = {"file": ("listing-video.mp4", video_bytes, "video/mp4")}

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(upload_url, data=data, files=files)
        except httpx.HTTPError as exc:
            raise VideoUploadError("Cloudinary video upload failed") from exc

    if response.status_code >= 400:
        raise VideoUploadError("Cloudinary video upload failed")

    try:
        payload = response.json()
    except ValueError as exc:
        raise VideoUploadError("Cloudinary returned invalid JSON") from exc

    secure_url = payload.get("secure_url")
    if not secure_url:
        raise VideoUploadError("Cloudinary returned no secure URL")
    return str(secure_url)
