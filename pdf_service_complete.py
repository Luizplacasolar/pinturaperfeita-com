"""
PINTURA PERFEITA — Microserviço PDF Completo
Arquivo: pdf_service_complete.py

Instalar:
    pip install fastapi uvicorn reportlab pillow python-multipart

Rodar:
    uvicorn pdf_service_complete:app --host 0.0.0.0 --port 8001 --workers 2

Deploy Railway/Render:
    Procfile: web: uvicorn pdf_service_complete:app --host 0.0.0.0 --port $PORT
"""

import io, os, json, tempfile, base64, sys
from datetime import datetime
from typing import Optional, Dict, Any

# ─── Importar os geradores ────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from pdf_templates import generate_pdf

# ─── FastAPI ─────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Pintura Perfeita — PDF Service",
    description="Microserviço de geração de PDFs premium para propostas, OS e recibos",
    version="2.0.0",
    docs_url="/docs",
)

# CORS — permitir chamadas do Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],               # Em produção: especificar domínio
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── Auth simples por token ───────────────────────────────────
PDF_SERVICE_SECRET = os.getenv("PDF_SERVICE_SECRET", "pp-secret-2026")

def check_auth(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(401, "Authorization header obrigatório")
    token = authorization.replace("Bearer ", "").strip()
    if token != PDF_SERVICE_SECRET:
        raise HTTPException(403, "Token inválido")


# ─── Modelos ─────────────────────────────────────────────────

class PdfRequest(BaseModel):
    template: str = Field("proposta", description="proposta | ordem_servico | recibo | relatorio_materiais")
    data: Dict[str, Any] = Field(..., description="Dados do documento")
    filename: Optional[str] = Field(None, description="Nome do arquivo (sem .pdf)")
    return_base64: bool = Field(False, description="Se True, retorna JSON com base64 ao invés de binário")


# ─── Endpoints ───────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pinturaperfeita-pdf",
        "version": "2.0.0",
        "templates": ["proposta", "ordem_servico", "recibo", "relatorio_materiais"],
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/generate")
async def generate(req: PdfRequest, authorization: Optional[str] = Header(None)):
    """
    Gera um PDF e retorna como download binário ou base64.
    
    Exemplos de body:
    
    Proposta:
    ```json
    {
      "template": "proposta",
      "data": {
        "code": "PP-A1B2C3",
        "company": {"name": "Pintura Perfeita Pro", ...},
        "client": {"name": "João Silva", ...},
        "calc": {"total": 12060.18, ...},
        "form": {"totalArea": 180, "paintType": "premium", ...}
      }
    }
    ```
    
    Recibo:
    ```json
    {
      "template": "recibo",
      "data": {
        "company": {...},
        "client": {...},
        "amount": 6030.09,
        "payment_method": "PIX",
        "payment_date": "03/05/2026"
      }
    }
    ```
    """
    check_auth(authorization)

    # Validações por template
    template = req.template
    data     = req.data

    validations = {
        "proposta":            lambda d: d.get("calc", {}).get("total"),
        "ordem_servico":       lambda d: d.get("calc"),
        "recibo":              lambda d: d.get("amount"),
        "relatorio_materiais": lambda d: True,
    }

    if template not in validations:
        raise HTTPException(400, f"Template '{template}' inválido. Opções: {list(validations)}")

    if not validations[template](data):
        raise HTTPException(400, f"Dados incompletos para template '{template}'")

    # Gerar em arquivo temporário
    suffix   = f"_{template}_{datetime.now().strftime('%H%M%S%f')}.pdf"
    tmp_path = os.path.join(tempfile.gettempdir(), f"pp{suffix}")

    try:
        generate_pdf(data, tmp_path, template)

        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()

    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar PDF: {str(e)}")
    finally:
        try: os.unlink(tmp_path)
        except: pass

    # Nome do arquivo
    code     = data.get("code", data.get("receipt_number", "documento"))
    fname    = req.filename or f"{template}-{code}"
    fname    = fname.replace("/", "-").replace(" ", "_")
    filename = f"{fname}.pdf"

    # Retornar base64 ou binário
    if req.return_base64:
        return JSONResponse({
            "success":    True,
            "template":   template,
            "filename":   filename,
            "size_bytes": len(pdf_bytes),
            "pdf_base64": base64.b64encode(pdf_bytes).decode(),
        })

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length":      str(len(pdf_bytes)),
            "X-Template":          template,
            "X-Filename":          filename,
        },
    )


@app.post("/preview")
async def preview(req: PdfRequest, authorization: Optional[str] = Header(None)):
    """Retorna PDF como inline (para visualização no browser)."""
    check_auth(authorization)

    tmp_path = os.path.join(tempfile.gettempdir(), f"pp_prev_{datetime.now().strftime('%H%M%S%f')}.pdf")
    try:
        generate_pdf(req.data, tmp_path, req.template)
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try: os.unlink(tmp_path)
        except: pass

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@app.post("/batch")
async def batch(request: Request, authorization: Optional[str] = Header(None)):
    """
    Gera múltiplos PDFs e retorna ZIP.
    Body: {"documents": [{"template": "...", "data": {...}, "filename": "..."}, ...]}
    """
    check_auth(authorization)

    import zipfile
    body = await request.json()
    documents = body.get("documents", [])

    if not documents:
        raise HTTPException(400, "Campo 'documents' é obrigatório e não pode ser vazio")
    if len(documents) > 20:
        raise HTTPException(400, "Máximo de 20 documentos por batch")

    zip_buffer = io.BytesIO()
    errors = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, doc in enumerate(documents):
            template = doc.get("template", "proposta")
            data     = doc.get("data", {})
            fname    = doc.get("filename", f"{template}_{i+1:02d}")

            tmp_path = os.path.join(tempfile.gettempdir(), f"pp_batch_{i}_{datetime.now().microsecond}.pdf")
            try:
                generate_pdf(data, tmp_path, template)
                with open(tmp_path, "rb") as f:
                    pdf_bytes = f.read()
                zf.writestr(f"{fname}.pdf", pdf_bytes)
            except Exception as e:
                errors.append({"index": i, "template": template, "error": str(e)})
            finally:
                try: os.unlink(tmp_path)
                except: pass

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="pinturaperfeita_docs_{ts}.zip"',
            "Content-Length": str(len(zip_bytes)),
            "X-Errors": json.dumps(errors),
            "X-Documents-Count": str(len(documents) - len(errors)),
        },
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
