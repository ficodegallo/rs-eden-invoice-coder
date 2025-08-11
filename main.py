# main.py
import io, os
import httpx
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel, AnyHttpUrl
import fitz  # PyMuPDF

API_KEY = os.getenv("API_KEY")

app = FastAPI(title="PDF Code Stamper")

class StampRequest(BaseModel):
    code: str
    file_url: AnyHttpUrl
    all_pages: bool = False
    top_offset_px: int = 10
    fontsize: float = 13.0

def stamp_pdf_bytes(pdf_bytes: bytes, code_text: str, all_pages=False, top_offset_px=10, fontsize=13.0) -> bytes:
    top_offset_pt = top_offset_px * 0.75  # px -> pt (≈96 dpi)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = range(len(doc)) if all_pages else [0]
    for i in pages:
        page = doc[i]
        pw = page.rect.width
        box_h = fontsize * 1.8
        rect = fitz.Rect(0, top_offset_pt, pw, top_offset_pt + box_h)
        page.insert_textbox(rect, f"Billing Code: {code_text}", fontname="helv", fontsize=fontsize, align=1)
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()

@app.post("/stamp", summary="Stamp billing code using a file URL")
async def stamp_endpoint(payload: StampRequest, x_api_key: str | None = Header(default=None, convert_underscores=False)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Download the temporary file URL provided by the GPT Action
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(str(payload.file_url))
            r.raise_for_status()
            pdf_bytes = r.content
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch file_url: {e}")
    try:
        stamped = stamp_pdf_bytes(pdf_bytes, payload.code, payload.all_pages, payload.top_offset_px, payload.fontsize)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF processing failed: {e}")
    return Response(content=stamped, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="invoice-coded.pdf"'} )
