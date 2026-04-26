from fastapi import APIRouter, File, HTTPException, UploadFile
from services.receipt_ai_service import extract_receipt_data_from_image_bytes

router = APIRouter(prefix="/receipts", tags=["Receipts"])


def _looks_like_image(file: UploadFile) -> bool:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()

    if content_type.startswith("image/"):
        return True

    image_exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    return filename.endswith(image_exts)


@router.post("/extract")
async def extract_receipt(file: UploadFile = File(...)):
    try:
        if not _looks_like_image(file):
            raise HTTPException(status_code=400, detail="Please upload an image file.")

        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        mime_type = file.content_type if (file.content_type or "").startswith("image/") else "image/jpeg"

        result = extract_receipt_data_from_image_bytes(
            image_bytes=image_bytes,
            mime_type=mime_type,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))