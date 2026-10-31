"""Renders a crop of the original book page, so a question can always be compared with the printed original."""
import hashlib
import io
import json
import threading

from django.conf import settings

from .catalog import manifest

_lock = threading.Lock()
_pdfs = {}
MAX_SEGMENTS = 8


class BadCrop(ValueError):
    pass


def clean_segments(raw):
    """Validated copy of the segment list from the query string: page, col (0/1), top and bottom in PDF points."""
    try:
        segs = json.loads(raw)
        if not isinstance(segs, list) or not 1 <= len(segs) <= MAX_SEGMENTS:
            raise BadCrop
        out = []
        for s in segs:
            page, col, top, bottom = int(s['page']), int(s['col']), float(s['top']), float(s['bottom'])
            if page < 1 or col not in (0, 1) or not 0 <= top < bottom <= 3000:
                raise BadCrop
            out.append({'page': page, 'col': col, 'top': top, 'bottom': bottom})
        return out
    except (KeyError, TypeError, ValueError):
        raise BadCrop


def _pdf(book):
    from pypdfium2 import PdfDocument

    if book not in _pdfs:
        _pdfs[book] = PdfDocument(str(settings.BOOKS_DIR / manifest()['books'][book]))
    return _pdfs[book]


def render(book, segs, scale=2.4):
    from PIL import Image

    parts = []
    for sg in segs:
        with _lock:
            pdf = _pdf(book)
            if sg['page'] > len(pdf):
                raise BadCrop
            page = pdf[sg['page'] - 1]
            W, H = page.get_size()
            img = page.render(scale=scale).to_pil().convert('RGB')
        x0, x1 = (0.071 * W, 0.5 * W - 3) if sg['col'] == 0 else (0.5 * W + 3, 0.929 * W)
        t, b = max(0, sg['top'] - 3), min(H, sg['bottom'] + 4)
        parts.append(img.crop((int(x0 * scale), int(t * scale), int(x1 * scale), int(b * scale))))
    w = max(p.width for p in parts)
    out = Image.new('RGB', (w, sum(p.height for p in parts) + 4 * (len(parts) - 1)), 'white')
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height + 4
    buf = io.BytesIO()
    out.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def crop_png(book, segs):
    """PNG bytes for the crop, cached on disk (the same key the standalone version used)."""
    key = hashlib.sha1(json.dumps([book, segs]).encode()).hexdigest()
    settings.CROP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = settings.CROP_CACHE_DIR / f'{key}.png'
    if f.exists():
        return f.read_bytes()
    data = render(book, segs)
    f.write_bytes(data)
    return data
