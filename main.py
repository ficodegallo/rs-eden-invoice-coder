import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import Response
import fitz  # PyMuPDF
import os

API_KEY = os.getenv("API_KEY")  # set this in your host

app = FastAPI(title="PDF Code Stamper")

def stamp_pdf(pdf_bytes: bytes, code_text: str, top_offset_px: int = 10, fontsize: float = 13) -> bytes:
    # convert ~pixels to PDF points (assuming 96 dpi): 1 px ≈ 0.75 pt
    top_offset_pt = top_offset_px * 0.75
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    page = doc[0]
    pw = page.rect.width
    box_h = fontsize * 1.8
    rect = fitz.Rect(0, top_offset_pt, pw, top_offset_pt + box_h)

    page.insert_textbox(
        rect,
        f"Billing Code: {code_text}",
        fontname="helv",
        fontsize=fontsize,
        align=1  # center
    )

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()

@app.post("/stamp", summary="Stamp billing code onto first page", response_description="Stamped PDF")
async def stamp_endpoint(
    file: UploadFile = File(..., description="Source PDF"),
    code: str = Form(..., description="Billing code text"),
    x_api_key: str | None = Header(default=None, convert_underscores=False)
):
    # simple API key check
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Please upload a PDF")

    src_bytes = await file.read()
    try:
        stamped = stamp_pdf(src_bytes, code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF processing failed: {e}")

    return Response(content=stamped, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="invoice-coded.pdf"'} )
