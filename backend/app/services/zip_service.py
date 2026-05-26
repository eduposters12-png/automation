from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import httpx


class ZipCreationError(Exception):
    pass


async def _download_asset(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        try:
            response = await client.get(url)
        except httpx.HTTPError as exc:
            raise ZipCreationError("Could not download listing asset") from exc
    if response.status_code >= 400 or not response.content:
        raise ZipCreationError("Could not download listing asset")
    return response.content


def _copy_text(listing: dict[str, Any]) -> str:
    tags = listing.get("tags") or []
    price = listing.get("price")
    return (
        "TITLE:\n"
        f"{listing.get('title') or ''}\n\n"
        "DESCRIPTION:\n"
        f"{listing.get('description') or ''}\n\n"
        "TAGS:\n"
        f"{', '.join(str(tag) for tag in tags)}\n\n"
        f"PRICE: ${price if price is not None else ''}\n"
    )


async def create_listing_zip(listing: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    image_urls = listing.get("image_urls") or []
    video_url = listing.get("video_url")
    pdf_url = listing.get("pdf_url")

    try:
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("listing-copy.txt", _copy_text(listing))
            for index, image_url in enumerate(image_urls):
                image_bytes = await _download_asset(str(image_url))
                archive.writestr(f"images/image-{index + 1}.jpg", image_bytes)
            if video_url:
                video_bytes = await _download_asset(str(video_url))
                archive.writestr("video/listing-video.mp4", video_bytes)
            if pdf_url:
                pdf_bytes = await _download_asset(str(pdf_url))
                archive.writestr("digital-product.pdf", pdf_bytes)
    except ZipCreationError:
        raise
    except Exception as exc:
        raise ZipCreationError("Could not create listing zip") from exc

    return buffer.getvalue()
