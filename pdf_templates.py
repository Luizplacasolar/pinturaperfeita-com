"""
PINTURA PERFEITA — Gerador de PDFs Multi-Template v2.0
Templates:
  1. Proposta Comercial (2 páginas)
  2. Ordem de Serviço
  3. Recibo de Pagamento
  4. Relatório de Materiais

Arquivo: pdf_templates.py
"""

import io, json, math, os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak, Image
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdf_canvas

# ─── Paleta ──────────────────────────────────────────────────
C = {
    "black":    colors.HexColor("#09090B"),
    "dark":     colors.HexColor("#111113"),
    "gold":     colors.HexColor("#C9A84C"),
    "gold_lt":  colors.HexColor("#E3C26A"),
    "gold_dim": colors.HexColor("#7A6020"),
    "gold_bg":  colors.HexColor("#FFFBF0"),
    "white":    colors.HexColor("#F4F4F0"),
    "gray_l":   colors.HexColor("#D4D4D8"),
    "gray":     colors.HexColor("#71717A"),
    "gray_d":   colors.HexColor("#3F3F46"),
    "light":    colors.HexColor("#FAFAF8"),
    "border":   colors.HexColor("#E4E4E7"),
    "green":    colors.HexColor("#16A34A"),
    "green_bg": colors.HexColor("#F0FDF4"),
    "red":      colors.HexColor("#DC2626"),
    "blue":     colors.HexColor("#2563EB"),
    "blue_bg":  colors.HexColor("#EFF6FF"),
    "dark_bg":  colors.HexColor("#F0EDE4"),
}

PW, PH = A4
ML = MR = 16*mm
MT = 20*mm
MB = 14*mm
CW = PW - ML - MR

# ─── Helpers ─────────────────────────────────────────────────
def brl(v): return f"R$ {float(v or 0):,.2f}".replace(",","X").replace(".",",").replace("X",".")
def dt(d):
    if not d: return "—"
    if isinstance(d, str):
        try: d = datetime.fromisoformat(d[:10])
        except: return d
    return d.strftime("%d/%m/%Y") if isinstance(d,(datetime,date)) else str(d)
def upper(s): return str(s or "").upper()


# ─── Flowables customizados ───────────────────────────────────

class HeaderBand(Flowable):
    """Cabeçalho negro com logo texto + contatos à direita."""
    def __init__(self, company, w, h=22*mm):
        super().__init__()
        self.company, self.w, self.h = company, w, h
    def wrap(self, *a): return self.w, self.h
    def draw(self):
        c = self.canv
        # Fundo preto
        c.setFillColor(C["black"])
        c.rect(0, 0, self.w, self.h, fill=1, stroke=0)
        # Faixa dourada inferior
        c.setFillColor(C["gold"])
        c.rect(0, 0, self.w*0.55, 1.5, fill=1, stroke=0)
        c.setFillColor(C["gold_dim"])
        c.rect(self.w*0.55, 0, self.w*0.3, 1.5, fill=1, stroke=0)
        # Nome empresa
        name = self.company.get("name","PINTURA PERFEITA").upper()
        c.setFillColor(C["gold"])
        c.setFont("Helvetica-Bold", 13)
        c.drawString(10, self.h - 10*mm, name)
        # Slogan
        c.setFillColor(C["gray"])
        c.setFont("Helvetica", 7)
        c.drawString(10, self.h - 14.5*mm, self.company.get("slogan","Soluções Profissionais em Pintura Predial"))
        # Contatos (direita)
        c.setFillColor(C["gray_l"])
        c.setFont("Helvetica", 7.5)
        phone   = self.company.get("phone","")
        email   = self.company.get("email","")
        website = self.company.get("website","pinturaperfeita.com")
        c.drawRightString(self.w - 8, self.h - 9*mm,  phone)
        c.drawRightString(self.w - 8, self.h - 13*mm, email)
        c.setFillColor(C["gold_dim"])
        c.drawRightString(self.w - 8, self.h - 17*mm, website)


class FooterBand(Flowable):
    """Rodapé preto com CNPJ e número de página."""
    def __init__(self, company, w, page_num=1):
        super().__init__()
        self.company, self.w, self.page_num = company, w, page_num
    def wrap(self, *a): return self.w, 10*mm
    def draw(self):
        c = self.canv
        c.setFillColor(C["black"])
        c.rect(0, 0, self.w, 10*mm, fill=1, stroke=0)
        c.setFillColor(C["gold"])
        c.rect(0, 10*mm - 1, self.w, 1, fill=1, stroke=0)
        name  = self.company.get("name","Pintura Perfeita")
        cnpj  = self.company.get("cnpj","")
        addr  = self.company.get("address","")
        c.setFillColor(C["gray"])
        c.setFont("Helvetica", 6.5)
        left = f"{name}  ·  CNPJ {cnpj}  ·  {addr}"
        c.drawString(8, 3.5*mm, left)
        c.setFillColor(C["gold"])
        c.setFont("Helvetica-Bold", 7)
        c.drawRightString(self.w - 8, 3.5*mm, f"Página {self.page_num}")


class SectionTitle(Flowable):
    """Título de seção com linha dourada."""
    def __init__(self, text, w):
        super().__init__()
        self.text, self.w = text, w
    def wrap(self, *a): return self.w, 14
    def draw(self):
        c = self.canv
        c.setFillColor(C["gold"])
        c.setFont("Helvetica-Bold", 7.5)
        tw = c.stringWidth(self.text, "Helvetica-Bold", 7.5)
        c.drawString(0, 3, self.text)
        # Linha após o texto
        c.setStrokeColor(C["gold_dim"])
        c.setLineWidth(0.6)
        c.line(tw + 6, 5, self.w, 5)
        c.setStrokeColor(C["border"])
        c.setLineWidth(0.3)
        c.line(0, 0, self.w, 0)


class GoldRect(Flowable):
    def __init__(self, w, h, color=None, radius=4):
        super().__init__()
        self.w, self.h = w, h
        self.color = color or C["gold_bg"]
        self.radius = radius
    def wrap(self, *a): return self.w, self.h
    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.w, self.h, self.radius, fill=1, stroke=0)


class QRPlaceholder(Flowable):
    def __init__(self, size=42, label=""):
        super().__init__()
        self.size, self.label = size, label
    def wrap(self, *a): return self.size, self.size + 10
    def draw(self):
        c = self.canv
        c.setFillColor(colors.white)
        c.roundRect(0, 10, self.size, self.size, 3, fill=1, stroke=0)
        c.setStrokeColor(C["black"])
        c.setLineWidth(0.5)
        c.roundRect(0, 10, self.size, self.size, 3, fill=0, stroke=1)
        # QR pattern visual
        sz = self.size / 9
        blocks = [(0,6),(1,6),(2,6),(3,6),(4,6),(5,6),(6,6),
                  (0,5),(6,5),(0,4),(2,4),(3,4),(4,4),(6,4),
                  (0,3),(6,3),(0,2),(2,2),(3,2),(4,2),(6,2),
                  (0,1),(6,1),(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),
                  (7,7),(8,7),(7,8),(8,8),(7,6),(8,5),(8,4),(7,3)]
        c.setFillColor(C["black"])
        for col,row in blocks:
            c.rect(col*sz+2, 10+row*sz+2, sz-0.8, sz-0.8, fill=1, stroke=0)
        if self.label:
            c.setFillColor(C["gray"])
            c.setFont("Helvetica", 5.5)
            c.drawCentredString(self.size/2, 4, self.label)


class SigLine(Flowable):
    def __init__(self, w, label="", sub=""):
        super().__init__()
        self.w, self.label, self.sub = w, label, sub
    def wrap(self, *a): return self.w, 26
    def draw(self):
        c = self.canv
        c.setStrokeColor(C["gray_d"])
        c.setLineWidth(0.5)
        c.line(0, 14, self.w, 14)
        c.setFillColor(C["gray"])
        c.setFont("Helvetica", 6.5)
        if self.label: c.drawCentredString(self.w/2, 6,  self.label)
        if self.sub:
            c.setFillColor(C["gray_d"])
            c.setFont("Helvetica", 5.5)
            c.drawCentredString(self.w/2, 0, self.sub)


def mk_style(**kw):
    base = dict(fontName="Helvetica", fontSize=9, textColor=C["black"], leading=13)
    base.update(kw)
    return ParagraphStyle("s", **base)


# ════════════════════════════════════════════════════════════
# TEMPLATE 1 — PROPOSTA COMERCIAL (2 páginas)
# ════════════════════════════════════════════════════════════

def _header_footer(company):
    def _fn(canv, doc):
        canv.saveState()
        w, h = A4
        # Header
        canv.setFillColor(C["black"])
        canv.rect(0, h - 18*mm, w, 18*mm, fill=1, stroke=0)
        canv.setFillColor(C["gold"])
        canv.rect(0, h - 18*mm - 1.5, w * 0.6, 1.5, fill=1, stroke=0)
        canv.setFillColor(C["gold_dim"])
        canv.rect(w * 0.6, h - 18*mm - 1.5, w * 0.3, 1.5, fill=1, stroke=0)
        name = company.get("name", "PINTURA PERFEITA").upper()
        canv.setFillColor(C["gold"])
        canv.setFont("Helvetica-Bold", 11)
        canv.drawString(ML, h - 9*mm, name)
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica", 6.5)
        canv.drawString(ML, h - 13.5*mm, company.get("slogan", "Soluções Profissionais em Pintura Predial"))
        canv.setFillColor(C["gray_l"])
        canv.setFont("Helvetica", 7)
        canv.drawRightString(w - MR, h - 9*mm,  company.get("phone", ""))
        canv.drawRightString(w - MR, h - 13*mm, company.get("email", ""))
        # Footer
        canv.setFillColor(C["black"])
        canv.rect(0, 0, w, 10*mm, fill=1, stroke=0)
        canv.setFillColor(C["gold"])
        canv.rect(0, 10*mm, w, 1, fill=1, stroke=0)
        cnpj = company.get("cnpj", "")
        addr = company.get("address", "")
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica", 6)
        canv.drawString(ML, 3.5*mm, f"{name}  ·  CNPJ {cnpj}  ·  {addr}")
        canv.setFillColor(C["gold"])
        canv.setFont("Helvetica-Bold", 6.5)
        canv.drawRightString(w - MR, 3.5*mm, f"Página {doc.page}")
        canv.restoreState()
    return _fn


def generate_proposta(est: dict, out: str) -> str:
    company = est.get("company", {})
    client  = est.get("client",  {})
    calc    = est.get("calc",    {})
    form    = est.get("form",    {})
    code    = est.get("code",    "PP-XXXXXX")
    items   = est.get("items",   [])
    ai_desc = est.get("ai_description", "")

    PROP_TYPES = {
        "casa_residencial":"Casa Residencial","apartamento":"Apartamento",
        "condominio":"Condomínio","bloco_residencial":"Bloco Residencial",
        "mansao":"Mansão","comercial":"Imóvel Comercial",
        "escritorio":"Escritório","galpao":"Galpão Industrial",
    }
    PAINT_NAMES = {
        "economica":"PVA Econômica","standard":"Acrílica Standard",
        "premium":"Acrílica Premium","luxo":"Látex Semibrilho",
        "textura":"Textura Acrílica","epoxy":"Epóxi Industrial",
    }

    doc = SimpleDocTemplate(out, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
        title=f"Proposta {code}", author=company.get("name","Pintura Perfeita"))

    S = {
        "h1":    mk_style(fontName="Helvetica-Bold", fontSize=22, textColor=C["black"], leading=26),
        "h2":    mk_style(fontName="Helvetica-Bold", fontSize=13, textColor=C["black"], leading=16),
        "h3":    mk_style(fontName="Helvetica-Bold", fontSize=10, textColor=C["black"], leading=13),
        "body":  mk_style(textColor=C["gray_d"], leading=14),
        "small": mk_style(fontSize=7.5, textColor=C["gray"], leading=11),
        "label": mk_style(fontName="Helvetica-Bold", fontSize=7, textColor=C["gray"],
                          leading=10, textTransform="uppercase"),
        "val":   mk_style(fontName="Helvetica-Bold", fontSize=10, textColor=C["black"], leading=13),
        "gold":  mk_style(fontName="Helvetica-Bold", fontSize=11, textColor=C["gold"], leading=14),
        "code":  mk_style(fontName="Courier-Bold",   fontSize=12, textColor=C["gold"], leading=15),
        "wh":    mk_style(fontName="Helvetica-Bold", fontSize=8,  textColor=colors.white, leading=11),
        "wh_lg": mk_style(fontName="Helvetica-Bold", fontSize=16, textColor=colors.white, leading=20),
        "gold_lg":mk_style(fontName="Helvetica-Bold",fontSize=22, textColor=C["gold"], leading=26),
        "obs":   mk_style(fontSize=8.5, textColor=C["gray_d"], leading=13),
        "green_bold": mk_style(fontName="Helvetica-Bold", fontSize=9, textColor=C["green"], leading=12),
    }

    story = []

    # ── PÁGINA 1 ─────────────────────────────────────────────
    story.append(Spacer(1, 3*mm))

    # Número + data
    row_top = Table([[
        Paragraph("PROPOSTA COMERCIAL", mk_style(fontSize=7.5, textColor=C["gray"], letterSpacing=1.5)),
        Paragraph(f'<font color="#C9A84C"><b>{code}</b></font>',
                  mk_style(fontName="Courier-Bold", fontSize=14, textColor=C["gold"], alignment=TA_RIGHT)),
    ]], colWidths=[CW*0.6, CW*0.4])
    row_top.setStyle(TableStyle([
        ("ALIGN",(1,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(row_top)
    story.append(Spacer(1,2*mm))
    # Linha dourada
    story.append(Table([[""]], colWidths=[CW],
        style=[("LINEBELOW",(0,0),(-1,-1),2,C["gold"]),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1, 4*mm))

    # Título + meta
    row_title = Table([[
        Paragraph(f"Proposta para<br/><b>{client.get('name','Cliente')}</b>", S["h1"]),
        Table([[
            Paragraph("Emissão", S["label"]),
            Paragraph(dt(est.get("created_at")), S["val"]),
        ],[
            Paragraph("Validade", S["label"]),
            Paragraph(f"{est.get('validity_days',30)} dias", S["val"]),
        ]], colWidths=[CW*0.15, CW*0.2],
        style=[("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
               ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4)]),
    ]], colWidths=[CW*0.6, CW*0.4])
    row_title.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(row_title)
    story.append(Spacer(1, 5*mm))

    # Grade info: cliente | imóvel
    def info_block(pairs, bg=C["light"]):
        rows = [[Paragraph(l, S["label"]), Paragraph(str(v or "—"), S["val"])] for l,v in pairs]
        t = Table(rows, colWidths=[CW*0.2, CW*0.28])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
            ("LINEBELOW",(0,0),(-1,-2),0.3,C["border"]),
        ]))
        return t

    prop_type = PROP_TYPES.get(str(form.get("propertyType","")), str(form.get("propertyType","")))
    left_pairs  = [("Cliente", client.get("name")), ("Telefone", client.get("phone")),
                   ("E-mail",  client.get("email")), ("Cidade",  client.get("city"))]
    right_pairs = [("Tipo de Imóvel", prop_type),
                   ("Área Total",  f"{form.get('totalArea',0)}m²"),
                   ("Condição",    str(form.get("wallCondition","")).capitalize()),
                   ("Endereço",    est.get("property_address","—"))]

    grid = Table([[info_block(left_pairs), Spacer(4*mm,1), info_block(right_pairs, C["gold_bg"])]],
                 colWidths=[CW*0.48, 4*mm, CW*0.48])
    grid.setStyle(TableStyle([
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(grid)
    story.append(Spacer(1, 5*mm))

    # Escopo dos serviços
    story.append(SectionTitle("ESCOPO DOS SERVIÇOS", CW))
    story.append(Spacer(1, 3*mm))
    svc_map = [
        ("hasInternal","Pintura Interna"),("hasExternal","Pintura Externa"),
        ("hasCeiling","Pintura de Tetos"),("hasMassaCorrida","Massa Corrida"),
        ("hasTexture","Textura / Grafiato"),("hasFacade","Fachada"),
        ("hasWalls","Muros Externos"),
    ]
    paint_nm = PAINT_NAMES.get(str(form.get("paintType","")), "Standard")
    active = [l for k,l in svc_map if form.get(k)]
    svc_items = active + [f"Tinta: {paint_nm}", f"{form.get('numCoats',2)}x Demãos",
                          f"Garantia: {est.get('warranty','1 ano')}"]
    cols3 = 3
    svc_rows = [svc_items[i:i+cols3] for i in range(0, len(svc_items), cols3)]
    while svc_rows and len(svc_rows[-1]) < cols3:
        svc_rows[-1].append("")
    svc_styled = []
    for row in svc_rows:
        svc_styled.append([
            Paragraph(
                f'<font color="#16A34A"><b>✓</b></font> {cell}' if i < len(active) + (row.index(cell) < len(active) % cols3 if svc_rows.index(row) == len(svc_rows)-1 else 0) else f'<font color="#71717A">◆</font> {cell}',
                mk_style(fontSize=8.5, textColor=C["gray_d"], leading=12)
            )
            for i, cell in enumerate(row)
        ])
    svc_t = Table(svc_styled, colWidths=[CW/3]*3)
    svc_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),C["light"]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("LINEBELOW",(0,0),(-1,-2),0.3,C["border"]),
    ]))
    story.append(svc_t)
    story.append(Spacer(1, 5*mm))

    # Descrição técnica (IA)
    if ai_desc:
        story.append(SectionTitle("DESCRIÇÃO TÉCNICA", CW))
        story.append(Spacer(1, 3*mm))
        desc_t = Table([[Paragraph(ai_desc, S["obs"])]], colWidths=[CW])
        desc_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),C["gold_bg"]),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LINEBEFORE",(0,0),(0,-1),3,C["gold"]),
        ]))
        story.append(desc_t)
        story.append(Spacer(1, 5*mm))

    # ── PÁGINA 2 ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 3*mm))

    # Materiais
    story.append(SectionTitle("MATERIAIS E INSUMOS", CW))
    story.append(Spacer(1, 3*mm))

    mat_header = [["Nº","DESCRIÇÃO","QTD.","UNID.","VALOR"]]
    paint_labels = {
        "economica":"Tinta PVA Econômica","standard":"Tinta Acrílica Standard Suvinil",
        "premium":"Tinta Acrílica Premium Coral","luxo":"Tinta Látex Semibrilho",
        "textura":"Textura Acrílica Quartzolit","epoxy":"Tinta Epóxi Industrial",
    }
    mat_items = [(paint_labels.get(str(form.get("paintType","")),"Tinta"),
                  f"{calc.get('paintLiters',0):.0f}", "litros", calc.get("paintCost",0))]
    if form.get("hasMassaCorrida"):
        mat_items.append(("Massa Corrida PVA", f"{calc.get('massaKg',0):.0f}", "kg", calc.get("massaCost",0)))
    mat_items += [
        ("Selador / Fundo Preparador", f"{calc.get('seladorL',0):.0f}", "litros", calc.get("seladorCost",0)),
        ("Rolos, Pincéis e Espátulas", f"{calc.get('rolos',1)}", "unid.", calc.get("rolos",1)*18),
        ("Fitas Crepe, Lixas, Plásticos", "1", "kit", max(0, calc.get("miscCost",0) - calc.get("rolos",1)*18)),
    ]
    mat_data = mat_header + [[str(i+1), d, q, u, brl(v)] for i,(d,q,u,v) in enumerate(mat_items)]
    mat_data.append(["","","","SUBTOTAL MATERIAIS", brl(calc.get("materialsCost",0))])

    cw = [8*mm, CW-8*mm-16*mm-12*mm-28*mm, 16*mm, 12*mm, 28*mm]
    mat_t = Table(mat_data, colWidths=cw, repeatRows=1)
    mat_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C["black"]),
        ("TEXTCOLOR",(0,0),(-1,0),C["gold"]),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),7.5),
        ("TOPPADDING",(0,0),(-1,0),7),("BOTTOMPADDING",(0,0),(-1,0),7),
        *[("BACKGROUND",(0,i),(-1,i),C["light"] if i%2==1 else colors.white) for i in range(1,len(mat_data)-1)],
        ("BACKGROUND",(0,-1),(-1,-1),C["dark_bg"]),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(3,-1),(-1,-1),C["gold"]),
        ("ALIGN",(0,0),(0,-1),"CENTER"),("ALIGN",(2,0),(4,-1),"RIGHT"),
        ("FONTSIZE",(0,1),(-1,-1),8.5),
        ("TOPPADDING",(0,1),(-1,-1),5),("BOTTOMPADDING",(0,1),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("LINEBELOW",(0,0),(-1,0),0.5,C["gold"]),
        ("LINEBELOW",(0,1),(-1,-2),0.3,C["border"]),
        ("LINEABOVE",(0,-1),(-1,-1),0.5,C["gold_dim"]),
    ]))
    story.append(mat_t)
    story.append(Spacer(1, 5*mm))

    # Mão de Obra
    story.append(SectionTitle("MÃO DE OBRA", CW))
    story.append(Spacer(1, 3*mm))

    nw = calc.get("numWorkers",1)
    nh = calc.get("numHelpers",0)
    wd = calc.get("workDays",1)
    wdr= form.get("workerDailyRate",280)
    hdr= form.get("helperDailyRate",180)
    lab_data = [
        ["PROFISSIONAL","QTDE","DIÁRIAS","R$/DIÁRIA","SUBTOTAL"],
        ["Pintor(es)", str(nw), str(wd), brl(wdr), brl(nw*wd*wdr)],
        ["Ajudante(s)", str(nh), str(wd), brl(hdr), brl(nh*wd*hdr)],
        ["","","","TOTAL MÃO DE OBRA", brl(calc.get("laborCost",0))],
    ]
    lw = [CW*0.3, CW*0.12, CW*0.14, CW*0.22, CW*0.22]
    lab_t = Table(lab_data, colWidths=lw, repeatRows=1)
    lab_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C["black"]),
        ("TEXTCOLOR",(0,0),(-1,0),C["gold"]),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7.5),
        ("TOPPADDING",(0,0),(-1,0),7),("BOTTOMPADDING",(0,0),(-1,0),7),
        ("BACKGROUND",(0,1),(-1,1),C["light"]),("BACKGROUND",(0,2),(-1,2),colors.white),
        ("BACKGROUND",(0,-1),(-1,-1),C["dark_bg"]),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),("TEXTCOLOR",(3,-1),(-1,-1),C["gold"]),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),("ALIGN",(3,0),(4,-1),"RIGHT"),
        ("FONTSIZE",(0,1),(-1,-1),8.5),
        ("TOPPADDING",(0,1),(-1,-1),5),("BOTTOMPADDING",(0,1),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("LINEBELOW",(0,0),(-1,0),0.5,C["gold"]),
        ("LINEBELOW",(0,1),(-1,-2),0.3,C["border"]),
        ("LINEABOVE",(0,-1),(-1,-1),0.5,C["gold_dim"]),
    ]))
    story.append(lab_t)
    story.append(Spacer(1, 5*mm))

    # Resumo financeiro
    story.append(SectionTitle("RESUMO FINANCEIRO", CW))
    story.append(Spacer(1, 3*mm))

    pm = form.get("profitMargin",30)
    fin_rows = [
        ("Subtotal Materiais",             calc.get("materialsCost",0), C["light"]),
        ("Subtotal Mão de Obra",           calc.get("laborCost",0),     colors.white),
        ("Subtotal",                       calc.get("subtotal",0),      C["dark_bg"]),
        (f"Margem Operacional ({pm:.0f}%)",calc.get("profit",0),        C["gold_bg"]),
    ]
    fin_data = [[Paragraph(l, S["body"]), Paragraph(brl(v), mk_style(fontName="Helvetica-Bold", fontSize=9, textColor=C["black"], alignment=TA_RIGHT))]
                for l,v,_ in fin_rows]
    fin_data.append([Paragraph("VALOR TOTAL DA PROPOSTA", S["wh_lg"]),
                     Paragraph(brl(calc.get("total",0)), S["gold_lg"])])
    fin_data.append([Paragraph(f"Equivalente a {brl(calc.get('pricePerM2',0))}/m²", S["small"]), Paragraph("",S["small"])])

    fin_t = Table(fin_data, colWidths=[CW*0.6, CW*0.4])
    bg_styles = [("BACKGROUND",(0,i),(-1,i),bg) for i,(_,__,bg) in enumerate(fin_rows)]
    fin_t.setStyle(TableStyle([
        *bg_styles,
        ("BACKGROUND",(0,len(fin_rows)),(-1,len(fin_rows)),C["black"]),
        ("BACKGROUND",(0,-1),(-1,-1),C["light"]),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("LINEBELOW",(0,0),(-1,-3),0.4,C["border"]),
        ("LINEABOVE",(0,len(fin_rows)),(-1,len(fin_rows)),2,C["gold"]),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(fin_t)
    story.append(Spacer(1, 5*mm))

    # Condições
    story.append(SectionTitle("CONDIÇÕES COMERCIAIS", CW))
    story.append(Spacer(1, 3*mm))
    cond = [
        ("Forma de Pagamento", est.get("payment_terms","50% entrada + 50% conclusão")),
        ("Garantia do Serviço", est.get("warranty","1 ano")),
        ("Prazo de Execução", f"{calc.get('workDays',1)} dias úteis"),
        ("Validade desta Proposta", f"{est.get('validity_days',30)} dias corridos"),
    ]
    cond_data = [[Paragraph(l, mk_style(fontName="Helvetica-Bold", fontSize=7.5, textColor=C["gold"])),
                  Paragraph(v, S["val"])] for l,v in cond]
    cond_t = Table(cond_data, colWidths=[CW*0.32, CW*0.68])
    cond_t.setStyle(TableStyle([
        *[("BACKGROUND",(0,i),(-1,i), C["gold_bg"] if i%2==0 else C["light"]) for i in range(len(cond))],
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("LINEBELOW",(0,0),(-1,-2),0.3,C["border"]),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(cond_t)

    obs = est.get("observations") or form.get("observations","")
    if obs:
        story.append(Spacer(1,4*mm))
        story.append(SectionTitle("OBSERVAÇÕES",CW))
        story.append(Spacer(1,3*mm))
        obs_t = Table([[Paragraph(obs, S["obs"])]], colWidths=[CW])
        obs_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),C["gold_bg"]),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LINEBEFORE",(0,0),(0,-1),3,C["gold"]),
        ]))
        story.append(obs_t)

    # Assinaturas
    story.append(Spacer(1, 6*mm))
    story.append(SectionTitle("APROVAÇÃO E ASSINATURA", CW))
    story.append(Spacer(1, 4*mm))

    aceite = (f"Eu, {client.get('name','___________________')}, declaro estar de acordo com os termos "
              f"desta proposta no valor de {brl(calc.get('total',0))} (Proposta {code}).")
    aceite_t = Table([[Paragraph(aceite, mk_style(fontSize=8.5, textColor=C["gray_d"], leading=13))]], colWidths=[CW])
    aceite_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),C["light"]),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(aceite_t)
    story.append(Spacer(1,6*mm))

    sig_l = Table([
        [SigLine(CW*0.44, client.get("name","Cliente"), f"CPF/CNPJ: {client.get('document','_______________')}")],
        [Spacer(1,4*mm)],
        [SigLine(CW*0.44, company.get("name","Empresa"), "Responsável Técnico")],
    ], colWidths=[CW*0.44], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])

    sig_r = Table([
        [Paragraph("DATA / LOCAL", mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"]))],
        [Spacer(1,2*mm)],
        [SigLine(CW*0.44)],
        [Spacer(1,5*mm)],
        [Paragraph("Aprovação via QR Code:", mk_style(fontSize=7.5,textColor=C["gray"]))],
        [Spacer(1,2*mm)],
        [QRPlaceholder(44, f"pp/{code}")],
    ], colWidths=[CW*0.44], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])

    sig_outer = Table([[sig_l, Spacer(CW*0.04,1), sig_r]], colWidths=[CW*0.47, CW*0.05, CW*0.47])
    sig_outer.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(sig_outer)
    story.append(Spacer(1,6*mm))

    # Faixa de selos
    seals = [["✓  EMPRESA CERTIFICADA","✓  MATERIAIS PREMIUM","✓  GARANTIA INCLUSA","✓  EQUIPE TREINADA"]]
    seal_t = Table([[Paragraph(s, mk_style(fontName="Helvetica-Bold",fontSize=7.5,textColor=C["gold"],alignment=TA_CENTER)) for s in seals[0]]], colWidths=[CW/4]*4)
    seal_t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),C["black"]),("ALIGN",(0,0),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    story.append(seal_t)

    doc.build(story, onFirstPage=_header_footer(company), onLaterPages=_header_footer(company))
    return out


# ════════════════════════════════════════════════════════════
# TEMPLATE 2 — ORDEM DE SERVIÇO
# ════════════════════════════════════════════════════════════

def generate_ordem_servico(est: dict, out: str) -> str:
    company = est.get("company", {})
    client  = est.get("client",  {})
    calc    = est.get("calc",    {})
    form    = est.get("form",    {})
    code    = est.get("code",    "PP-XXXXXX")
    os_num  = f"OS-{code.replace('PP-','')}"

    doc = SimpleDocTemplate(out, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=14*mm, bottomMargin=14*mm,
        title=f"Ordem de Serviço {os_num}")

    story = []

    def hf(canv, d):
        canv.saveState()
        w,h = A4
        # Header compacto
        canv.setFillColor(C["black"])
        canv.rect(0, h-14*mm, w, 14*mm, fill=1, stroke=0)
        canv.setFillColor(C["gold"])
        canv.rect(0, h-14*mm-1, w*0.5, 1, fill=1, stroke=0)
        canv.setFont("Helvetica-Bold", 10)
        canv.setFillColor(C["gold"])
        canv.drawString(ML, h-8*mm, company.get("name","PINTURA PERFEITA").upper())
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica", 7)
        canv.drawRightString(w-MR, h-8*mm, "ORDEM DE SERVIÇO")
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 9)
        canv.drawRightString(w-MR, h-12*mm, os_num)
        # Footer
        canv.setFillColor(C["black"])
        canv.rect(0,0,w,8*mm,fill=1,stroke=0)
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica", 6)
        canv.drawString(ML, 2.5*mm, f"CNPJ: {company.get('cnpj','')}  ·  {company.get('email','')}  ·  {company.get('phone','')}")
        canv.setFillColor(C["gold"])
        canv.setFont("Helvetica-Bold", 6.5)
        canv.drawRightString(w-MR, 2.5*mm, f"Pág. {d.page}")
        canv.restoreState()

    story.append(Spacer(1, 3*mm))

    # Cabeçalho OS
    header_data = [[
        Table([[Paragraph("ORDEM DE SERVIÇO", mk_style(fontName="Helvetica-Bold",fontSize=18,textColor=C["black"],leading=22))],
               [Paragraph(f"Nº {os_num}", mk_style(fontName="Courier-Bold",fontSize=13,textColor=C["gold"],leading=16))]],
               colWidths=[CW*0.55], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),2),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]),
        Table([[Paragraph("Data de Emissão", mk_style(fontName="Helvetica-Bold",fontSize=7.5,textColor=C["gray"]))],
               [Paragraph(dt(est.get("created_at")), mk_style(fontName="Helvetica-Bold",fontSize=11,textColor=C["black"]))],
               [Spacer(1,3*mm)],
               [Paragraph("Status", mk_style(fontName="Helvetica-Bold",fontSize=7.5,textColor=C["gray"]))],
               [Paragraph("EM EXECUÇÃO", mk_style(fontName="Helvetica-Bold",fontSize=10,textColor=C["green"]))]],
               colWidths=[CW*0.35], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),2),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("ALIGN",(0,0),(-1,-1),"RIGHT")]),
    ]]
    h_tbl = Table(header_data, colWidths=[CW*0.6, CW*0.4])
    h_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
    story.append(h_tbl)
    story.append(Spacer(1,2*mm))
    story.append(Table([[""]], colWidths=[CW], style=[("LINEBELOW",(0,0),(-1,-1),2,C["gold"]),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1,5*mm))

    # Info cliente + imóvel
    story.append(SectionTitle("DADOS DO CLIENTE E IMÓVEL", CW))
    story.append(Spacer(1,3*mm))
    cl_data = [
        [Paragraph("CLIENTE",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"])),
         Paragraph(client.get("name","—"),mk_style(fontName="Helvetica-Bold",fontSize=10,textColor=C["black"])),
         Paragraph("TELEFONE",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"])),
         Paragraph(client.get("phone","—"),mk_style(fontSize=9,textColor=C["black"]))],
        [Paragraph("E-MAIL",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"])),
         Paragraph(client.get("email","—"),mk_style(fontSize=9,textColor=C["black"])),
         Paragraph("CIDADE",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"])),
         Paragraph(client.get("city","—"),mk_style(fontSize=9,textColor=C["black"]))],
        [Paragraph("ENDEREÇO DA OBRA",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"])),
         Paragraph(est.get("property_address","—"),mk_style(fontSize=9,textColor=C["black"])),
         Paragraph("ÁREA",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=C["gray"])),
         Paragraph(f"{form.get('totalArea',0)}m²",mk_style(fontName="Helvetica-Bold",fontSize=9,textColor=C["black"]))],
    ]
    cl_t = Table(cl_data, colWidths=[CW*0.2, CW*0.3, CW*0.18, CW*0.32])
    cl_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),C["light"]),
        *[("BACKGROUND",(0,i),(-1,i), C["gold_bg"] if i%2==0 else C["light"]) for i in range(len(cl_data))],
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW",(0,0),(-1,-2),0.3,C["border"]),
    ]))
    story.append(cl_t)
    story.append(Spacer(1,5*mm))

    # Cronograma
    story.append(SectionTitle("CRONOGRAMA DE EXECUÇÃO", CW))
    story.append(Spacer(1,3*mm))
    cron_data = [
        ["INÍCIO PREVISTO","TÉRMINO PREVISTO","DIAS ÚTEIS","Nº PINTORES","Nº AJUDANTES"],
        [est.get("start_date","—"), est.get("end_date","—"),
         str(calc.get("workDays","—")), str(calc.get("numWorkers","—")), str(calc.get("numHelpers","—"))],
    ]
    cron_t = Table(cron_data, colWidths=[CW/5]*5, repeatRows=1)
    cron_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C["black"]),("TEXTCOLOR",(0,0),(-1,0),C["gold"]),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7),
        ("BACKGROUND",(0,1),(-1,1),C["gold_bg"]),
        ("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("FONTSIZE",(0,1),(-1,1),11),
        ("TEXTCOLOR",(0,1),(-1,1),C["black"]),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW",(0,0),(-1,0),0.5,C["gold"]),
    ]))
    story.append(cron_t)
    story.append(Spacer(1,5*mm))

    # Serviços a executar
    story.append(SectionTitle("SERVIÇOS A EXECUTAR", CW))
    story.append(Spacer(1,3*mm))
    svc_os = [
        ("hasInternal","Pintura Interna das paredes"),
        ("hasExternal","Pintura Externa"),
        ("hasCeiling","Pintura de Tetos"),
        ("hasMassaCorrida","Aplicação de Massa Corrida"),
        ("hasTexture","Aplicação de Textura / Grafiato"),
        ("hasFacade","Pintura de Fachada"),
        ("hasWalls","Pintura de Muros Externos"),
    ]
    svc_rows2 = []
    for i, (k,l) in enumerate(svc_os):
        if form.get(k):
            svc_rows2.append([
                Paragraph(f"<b>{i+1:02d}</b>", mk_style(fontName="Courier-Bold",fontSize=9,textColor=C["gold"],alignment=TA_CENTER)),
                Paragraph(f"<b>{l}</b>", mk_style(fontName="Helvetica-Bold",fontSize=9,textColor=C["black"])),
                Paragraph("☐ Concluído", mk_style(fontSize=8.5,textColor=C["gray"],alignment=TA_RIGHT)),
            ])
    if svc_rows2:
        svc_t2 = Table(svc_rows2, colWidths=[10*mm, CW-10*mm-35*mm, 35*mm])
        svc_t2.setStyle(TableStyle([
            *[("BACKGROUND",(0,i),(-1,i), C["light"] if i%2==0 else colors.white) for i in range(len(svc_rows2))],
            ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LINEBELOW",(0,0),(-1,-2),0.3,C["border"]),
        ]))
        story.append(svc_t2)
    story.append(Spacer(1,5*mm))

    # Materiais necessários
    story.append(SectionTitle("MATERIAIS NECESSÁRIOS", CW))
    story.append(Spacer(1,3*mm))
    paint_labels = {"economica":"Tinta PVA Econômica","standard":"Tinta Acrílica Standard",
                    "premium":"Tinta Acrílica Premium","luxo":"Tinta Látex Semibrilho",
                    "textura":"Textura Acrílica","epoxy":"Tinta Epóxi Industrial"}
    mat_os = [
        (paint_labels.get(str(form.get("paintType","")),"Tinta"), f"{calc.get('paintLiters',0):.0f} litros"),
    ]
    if form.get("hasMassaCorrida"):
        mat_os.append(("Massa Corrida PVA", f"{calc.get('massaKg',0):.0f} kg"))
    mat_os += [
        ("Selador / Fundo Preparador", f"{calc.get('seladorL',0):.0f} litros"),
        ("Rolos de Lã 23cm", f"{calc.get('rolos',1)} unidades"),
        ("Fitas Crepe e Lixas", "1 kit"),
        ("Plásticos de Proteção", "1 kit"),
    ]
    mat_os_data = [["MATERIAL","QUANTIDADE","☐ OK"]] + [[m,q,""] for m,q in mat_os]
    mat_os_t = Table(mat_os_data, colWidths=[CW*0.55, CW*0.3, CW*0.15], repeatRows=1)
    mat_os_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C["black"]),("TEXTCOLOR",(0,0),(-1,0),C["gold"]),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7.5),
        ("TOPPADDING",(0,0),(-1,0),7),("BOTTOMPADDING",(0,0),(-1,0),7),
        *[("BACKGROUND",(0,i),(-1,i), C["light"] if i%2==1 else colors.white) for i in range(1,len(mat_os_data))],
        ("FONTSIZE",(0,1),(-1,-1),8.5),
        ("TOPPADDING",(0,1),(-1,-1),6),("BOTTOMPADDING",(0,1),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW",(0,0),(-1,0),0.5,C["gold"]),
        ("LINEBELOW",(0,1),(-1,-2),0.3,C["border"]),
        ("ALIGN",(1,0),(2,-1),"CENTER"),
    ]))
    story.append(mat_os_t)
    story.append(Spacer(1,5*mm))

    # Valor e assinatura
    story.append(SectionTitle("VALOR E ASSINATURA", CW))
    story.append(Spacer(1,3*mm))
    val_data = [[
        Table([[Paragraph("VALOR TOTAL",mk_style(fontName="Helvetica-Bold",fontSize=8,textColor=colors.white))],
               [Paragraph(brl(calc.get("total",0)),mk_style(fontName="Helvetica-Bold",fontSize=18,textColor=C["gold"],leading=22))],
               [Paragraph(est.get("payment_terms","50% entrada + 50% conclusão"),mk_style(fontSize=8,textColor=C["gray_l"]))]], colWidths=[CW*0.4],
         style=[("BACKGROUND",(0,0),(-1,-1),C["black"]),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10)]),
        Spacer(6*mm,1),
        Table([[SigLine(CW*0.48, client.get("name","Cliente"), "Assinatura do Cliente")],
               [Spacer(1,5*mm)],
               [SigLine(CW*0.48, company.get("name","Responsável"), "Responsável Técnico")]], colWidths=[CW*0.48],
         style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]),
    ]]
    val_t = Table(val_data, colWidths=[CW*0.42, 6*mm, CW*0.52])
    val_t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
    story.append(val_t)

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return out


# ════════════════════════════════════════════════════════════
# TEMPLATE 3 — RECIBO DE PAGAMENTO
# ════════════════════════════════════════════════════════════

def generate_recibo(data: dict, out: str) -> str:
    company  = data.get("company", {})
    client   = data.get("client",  {})
    amount   = data.get("amount",  0)
    desc     = data.get("description", "Serviços de pintura")
    code     = data.get("estimate_code", "—")
    rec_num  = data.get("receipt_number", f"REC-{datetime.now().strftime('%Y%m%d%H%M')}")
    pay_meth = data.get("payment_method", "PIX")
    pay_date = data.get("payment_date", datetime.now().strftime("%d/%m/%Y"))
    installment = data.get("installment", "")  # ex: "1/2"

    doc = SimpleDocTemplate(out, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=16*mm, bottomMargin=16*mm,
        title=f"Recibo {rec_num}")

    story = []

    def hf_rec(canv, d):
        canv.saveState()
        w,h = A4
        canv.setFillColor(C["black"])
        canv.rect(0, h-12*mm, w, 12*mm, fill=1, stroke=0)
        canv.setFillColor(C["gold"])
        canv.rect(0, h-12*mm-1, w*0.4, 1, fill=1, stroke=0)
        canv.setFont("Helvetica-Bold", 10)
        canv.setFillColor(C["gold"])
        canv.drawString(ML, h-7.5*mm, company.get("name","PINTURA PERFEITA").upper())
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 8)
        canv.drawRightString(w-MR, h-7.5*mm, "RECIBO DE PAGAMENTO")
        canv.restoreState()

    story.append(Spacer(1,2*mm))

    # Número do recibo + valor (destaque visual)
    top_data = [[
        Table([[Paragraph("RECIBO DE PAGAMENTO",mk_style(fontName="Helvetica-Bold",fontSize=16,textColor=C["black"],leading=20))],
               [Paragraph(rec_num,mk_style(fontName="Courier-Bold",fontSize=11,textColor=C["gold"]))]],
               colWidths=[CW*0.55], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),2),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]),
        Table([[Paragraph("VALOR RECEBIDO",mk_style(fontName="Helvetica-Bold",fontSize=7,textColor=colors.white,alignment=TA_CENTER))],
               [Paragraph(brl(amount),mk_style(fontName="Helvetica-Bold",fontSize=22,textColor=C["gold"],leading=26,alignment=TA_CENTER))],
               [Paragraph(installment or pay_meth, mk_style(fontSize=8,textColor=C["gray"],alignment=TA_CENTER))]],
               colWidths=[CW*0.38], style=[("BACKGROUND",(0,0),(-1,-1),C["black"]),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]),
    ]]
    top_t = Table(top_data, colWidths=[CW*0.58, CW*0.42])
    top_t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
    story.append(top_t)
    story.append(Spacer(1,2*mm))
    story.append(Table([[""]], colWidths=[CW], style=[("LINEBELOW",(0,0),(-1,-1),2,C["gold"]),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1,5*mm))

    # Corpo do recibo
    recibo_text = (
        f"Recebi(emos) de <b>{client.get('name','___________________')}</b>, "
        f"CPF/CNPJ: <b>{client.get('document','_______________')}</b>, "
        f"a importância de <b>{brl(amount)}</b> "
        f"referente a: <b>{desc}</b> "
        f"(Orçamento {code}), "
        f"pela forma de pagamento: <b>{pay_meth}</b>."
    )
    story.append(Table([[Paragraph(recibo_text, mk_style(fontSize=10, textColor=C["black"], leading=17))]], colWidths=[CW]))
    story.append(Spacer(1,5*mm))

    # Detalhes
    det_data = [
        ["DATA DO PAGAMENTO", "FORMA DE PAGAMENTO", "ORÇAMENTO / OBRA", "PARCELA"],
        [pay_date, pay_meth, code, installment or "Único"],
    ]
    det_t = Table(det_data, colWidths=[CW/4]*4, repeatRows=1)
    det_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C["black"]),("TEXTCOLOR",(0,0),(-1,0),C["gold"]),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7),
        ("BACKGROUND",(0,1),(-1,1),C["gold_bg"]),
        ("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("FONTSIZE",(0,1),(-1,1),11),
        ("TEXTCOLOR",(0,1),(-1,1),C["black"]),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW",(0,0),(-1,0),0.5,C["gold"]),
    ]))
    story.append(det_data and det_t)
    story.append(Spacer(1,8*mm))

    # Assinaturas
    sig_data = [[
        SigLine(CW*0.44, company.get("name","Empresa"), "Quem Recebeu"),
        Spacer(CW*0.1,1),
        SigLine(CW*0.44, client.get("name","Cliente"), "Quem Pagou"),
    ]]
    sig_t = Table(sig_data, colWidths=[CW*0.44, CW*0.12, CW*0.44])
    sig_t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"BOTTOM")]))
    story.append(sig_t)
    story.append(Spacer(1,6*mm))

    # Local e data
    city = company.get("city","São Paulo")
    story.append(Paragraph(
        f"{city}, {pay_date}",
        mk_style(fontSize=9, textColor=C["gray"], alignment=TA_CENTER)
    ))
    story.append(Spacer(1,5*mm))

    # Nota de validade
    story.append(Table([[Paragraph(
        "⚠  Este recibo é válido como comprovante de pagamento. Guarde-o para referência futura.",
        mk_style(fontSize=7.5, textColor=C["gray_d"], alignment=TA_CENTER)
    )]], colWidths=[CW]))

    doc.build(story, onFirstPage=hf_rec, onLaterPages=hf_rec)
    return out


# ════════════════════════════════════════════════════════════
# TEMPLATE 4 — RELATÓRIO DE MATERIAIS
# ════════════════════════════════════════════════════════════

def generate_relatorio_materiais(data: dict, out: str) -> str:
    company   = data.get("company", {})
    materials = data.get("materials", [])
    period    = data.get("period", datetime.now().strftime("%B %Y"))
    estimates = data.get("estimates", [])

    doc = SimpleDocTemplate(out, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=16*mm, bottomMargin=14*mm,
        title=f"Relatório de Materiais — {period}")

    story = []

    def hf_rel(canv, d):
        canv.saveState()
        w,h = A4
        canv.setFillColor(C["black"])
        canv.rect(0, h-13*mm, w, 13*mm, fill=1, stroke=0)
        canv.setFillColor(C["gold"])
        canv.setFont("Helvetica-Bold", 10)
        canv.drawString(ML, h-8*mm, company.get("name","PINTURA PERFEITA").upper())
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica", 7)
        canv.drawRightString(w-MR, h-8*mm, f"RELATÓRIO DE MATERIAIS — {period.upper()}")
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica", 6)
        canv.drawRightString(w-MR, h-12*mm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canv.setFillColor(C["black"])
        canv.rect(0,0,w,8*mm,fill=1,stroke=0)
        canv.setFillColor(C["gray"])
        canv.setFont("Helvetica",6)
        canv.drawString(ML, 2.5*mm, f"CNPJ: {company.get('cnpj','')}  ·  {company.get('email','')}")
        canv.setFillColor(C["gold"])
        canv.setFont("Helvetica-Bold",6.5)
        canv.drawRightString(w-MR, 2.5*mm, f"Pág. {d.page}")
        canv.restoreState()

    story.append(Spacer(1,3*mm))
    story.append(Paragraph(f"Relatório de Materiais", mk_style(fontName="Helvetica-Bold",fontSize=20,textColor=C["black"],leading=24)))
    story.append(Paragraph(period, mk_style(fontName="Helvetica-Bold",fontSize=12,textColor=C["gold"],leading=15)))
    story.append(Spacer(1,2*mm))
    story.append(Table([[""]], colWidths=[CW], style=[("LINEBELOW",(0,0),(-1,-1),2,C["gold"]),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1,5*mm))

    # Catálogo de materiais
    story.append(SectionTitle("CATÁLOGO DE MATERIAIS ATIVOS", CW))
    story.append(Spacer(1,3*mm))

    if materials:
        cats = sorted(set(m.get("category","outros") for m in materials))
        for cat in cats:
            cat_items = [m for m in materials if m.get("category") == cat]
            if not cat_items: continue
            story.append(Paragraph(cat.upper(), mk_style(fontName="Helvetica-Bold",fontSize=8,textColor=C["gold_dim"],leading=12)))
            story.append(Spacer(1,2*mm))
            cat_data = [["MATERIAL","MARCA","UNIDADE","PREÇO","RENDIMENTO"]]
            for m in cat_items:
                cat_data.append([
                    m.get("name","—"), m.get("brand","—"), m.get("unit","—"),
                    brl(m.get("price",0)),
                    f"{m.get('yield_per_unit','—')}m²/{m.get('unit','un')}" if m.get("yield_per_unit") else "—",
                ])
            cw_cat = [CW*0.38, CW*0.18, CW*0.12, CW*0.16, CW*0.16]
            cat_t = Table(cat_data, colWidths=cw_cat, repeatRows=1)
            cat_t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),C["black"]),("TEXTCOLOR",(0,0),(-1,0),C["gold"]),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7),
                ("TOPPADDING",(0,0),(-1,0),6),("BOTTOMPADDING",(0,0),(-1,0),6),
                *[("BACKGROUND",(0,i),(-1,i), C["light"] if i%2==1 else colors.white) for i in range(1,len(cat_data))],
                ("FONTSIZE",(0,1),(-1,-1),8),
                ("TOPPADDING",(0,1),(-1,-1),5),("BOTTOMPADDING",(0,1),(-1,-1),5),
                ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
                ("LINEBELOW",(0,0),(-1,0),0.5,C["gold"]),
                ("LINEBELOW",(0,1),(-1,-2),0.3,C["border"]),
                ("ALIGN",(2,0),(4,-1),"RIGHT"),
            ]))
            story.append(cat_t)
            story.append(Spacer(1,4*mm))

    doc.build(story, onFirstPage=hf_rel, onLaterPages=hf_rel)
    return out


# ════════════════════════════════════════════════════════════
# DISPATCHER — escolhe o template pelo tipo
# ════════════════════════════════════════════════════════════

def generate_pdf(data: dict, out: str, template: str = "proposta") -> str:
    """
    Gera PDF pelo template especificado.
    
    Templates disponíveis:
      - proposta          → Proposta Comercial completa (2 páginas)
      - ordem_servico     → Ordem de Serviço
      - recibo            → Recibo de Pagamento
      - relatorio_materiais → Relatório de Materiais
    """
    generators = {
        "proposta":            generate_proposta,
        "ordem_servico":       generate_ordem_servico,
        "recibo":              generate_recibo,
        "relatorio_materiais": generate_relatorio_materiais,
    }
    fn = generators.get(template)
    if not fn:
        raise ValueError(f"Template '{template}' não encontrado. Opções: {list(generators)}")
    return fn(data, out)


# ─── CLI ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--template", default="proposta")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = generate_pdf(data, args.output, args.template)
    print(f"PDF gerado: {result}", file=sys.stderr)
