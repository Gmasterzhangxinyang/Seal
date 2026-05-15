import cv2
from pyzxing import BarCodeReader

_QR_TYPE_MAP = {
    "LEAVE": "leave",
    "EXPENSE": "expense",
    "CERT": "cert",
}

_reader = BarCodeReader()


def scan_qr(image_path: str) -> tuple[str | None, str]:
    """
    扫描图片中的二维码/条形码。
    返回:
        qr_raw   - 二维码原始文本（无二维码则为 None）
        doc_type - 识别出的文件类型（无法识别则为 'general'）
    """
    results = _reader.decode(image_path)

    if not results:
        return None, "general"

    first_result = results[0] if isinstance(results, list) else next(iter(results.values()))
    raw = first_result.get("parsed") or first_result.get("raw")
    if not raw:
        return None, "general"
    qr_raw = raw.decode("utf-8").strip() if isinstance(raw, bytes) else str(raw).strip()
    if not qr_raw:
        return None, "general"

    doc_type = "general"
    for prefix, dtype in _QR_TYPE_MAP.items():
        if qr_raw.upper().startswith(prefix):
            doc_type = dtype
            break

    return qr_raw, doc_type
