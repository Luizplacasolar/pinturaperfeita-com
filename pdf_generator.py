"""
PINTURA PERFEITA — Gerador de PDF Premium
Geração server-side com reportlab
Arquivo: pdf_generator.py
"""

import io
import json
import math
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics import renderPDF

# ─── Paleta de cores ──────────────────────────────────────────
BLACK      = colors.HexColor("#09090B")
DARK       = colors.HexColor("#111113")
SURFACE    = colors.HexColor("#17171A")
GOLD       = colors.HexColor("#C9A84C")
GOLD_LIGHT = colors.HexColor("#E3C26A")
GOLD_DIM   = colors.HexColor("#7A6020")
WHITE      = colors.HexColor("#F4F4F0")
GRAY_L     = colors.HexColor("#D4D4D8")
GRAY       = colors.HexColor("#71717A")
GRAY_D     = colors.HexColor("#3F3F46")
GREEN      = colors.HexColor("#22C55E")
RED        = colors.HexColor("#EF4444")
BLUE       = colors.HexColor("#3B82F6")
LIGHT_BG   = colors.HexColor("#FAFAF8")
GOLD_BG    = colors.HexColor("#FDF8EE")
BORDER     = colors.HexColor("#E4E4E7")
DARK_BG    = colors.HexColor("#F0EDE4")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ─── Custom Flowables ─────────────────────────────────────────

class ColorRect(Flowable):
    """Retângulo colorido simples."""
    def __init__(self, w, h, fill, radius=0):
        super().__init__()
        self.w, self.h, self.fill, self.radius = w, h, fill, radius
    def wrap(self, *args): return self.w, self.h
    def draw(self):
        self.canv.setFillColor(self.fill)
        if self.radius:
            self.canv.roundRect(0, 0, self.w, self.h, self.radius, fill=1, stroke=0)
        else:
            self.canv.rect(0, 0, self.w, self.h, fill=1, stroke=0)


class GoldDivider(Flowable):
    """Linha divisória dourada com gradiente visual."""
    def __init__(self, w, h=1):
        super().__init__()
        self.w, self.h = w, h
    def wrap(self, *args): return self.w, self.h + 4
    def draw(self):
        c = self.canv
        c.setFillColor(GOLD)
        c.rect(0, 2, self.w * 0.6, self.h, fill=1, stroke=0)
        c.setFillColor(GOLD_DIM)
        c.rect(self.w * 0.6, 2, self.w * 0.3, self.h, fill=1, stroke=0)
        c.setFillColor(BORDER)
        c.rect(self.w * 0.9, 2, self.w * 0.1, self.h, fill=1, stroke=0)


class StarRating(Flowable):
    """Exibe estrelas de avaliação."""
    def __init__(self, rating=5, size=8):
        super().__init__()
        self.rating, self.size = rating, size
        self.total_w = 5 * (size + 2)
    def wrap(self, *args): return self.total_w, self.size + 2
    def draw(self):
        for i in range(5):
            x = i * (self.size + 2)
            self.canv.setFillColor(GOLD if i < self.rating else GRAY_D)
            # Estrela simplificada com circle
            self.canv.circle(x + self.size/2, self.size/2, self.size/2 * 0.8, fill=1, stroke=0)


class QRCodeBox(Flowable):
    """Placeholder visual para QR Code."""
    def __init__(self, size=40, text=""):
        super().__init__()
        self.size = size
        self.text = text
    def wrap(self, *args): return self.size, self.size
    def draw(self):
        c = self.canv
        c.setFillColor(colors.white)
        c.rect(0, 0, self.size, self.size, fill=1, stroke=0)
        c.setStrokeColor(BLACK)
        c.setLineWidth(0.5)
        c.rect(0, 0, self.size, self.size, fill=0, stroke=1)
        # Mini QR pattern visual
        cell = self.size / 10
        pattern = [
            (0,7),(1,7),(2,7),(3,7),(4,7),(5,7),(6,7),
            (0,6),(6,6),(0,5),(2,5),(3,5),(4,5),(6,5),
            (0,4),(2,4),(4,4),(6,4),(0,3),(6,3),
            (0,2),(2,2),(3,2),(4,2),(6,2),(0,1),(6,1),
            (0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),
            (8,8),(9,8),(8,9),(9,9),(8,7),(9,7),
            (8,5),(9,5),(8,4),(9,4),
        ]
        c.setFillColor(BLACK)
        for (col, row) in pattern:
            x = col * cell + 2
            y = row * cell + 2
            c.rect(x, y, cell - 0.5, cell - 0.5, fill=1, stroke=0)
        c.setFillColor(GRAY)
        c.setFontSize(4)
        c.drawCentredString(self.size / 2, -6, self.text[:20])


class SignatureLine(Flowable):
    """Linha de assinatura com label."""
    def __init__(self, w, label="", sublabel=""):
        super().__init__()
        self.w, self.label, self.sublabel = w, label, sublabel
    def wrap(self, *args): return self.w, 28
    def draw(self):
        c = self.canv
        c.setStrokeColor(GRAY_D)
        c.setLineWidth(0.5)
        c.line(0, 14, self.w, 14)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        if self.label:
            c.drawCentredString(self.w / 2, 6, self.label)
        if self.sublabel:
            c.setFillColor(colors.HexColor("#A0A0A0"))
            c.setFont("Helvetica", 6)
            c.drawCentredString(self.w / 2, 0, self.sublabel)


# ─── Header / Footer via canvas ───────────────────────────────

def make_header_footer(company: dict):
    def _draw(canv, doc):
        canv.saveState()
        w, h = A4

        # ── Barra de topo preta ──
        canv.setFillColor(BLACK)
        canv.rect(0, h - 14*mm, w, 14*mm, fill=1, stroke=0)

        # Logo/nome empresa
        canv.setFillColor(GOLD)
        canv.setFont("Helvetica-Bold", 11)
        canv.drawString(MARGIN, h - 9*mm, company.get("name", "PINTURA PERFEITA").upper())

        # Slogan
        canv.setFillColor(colors.HexColor("#8B8B8B"))
        canv.setFont("Helvetica", 7)
        canv.drawString(MARGIN, h - 12.5*mm, company.get("slogan", "Soluções Profissionais em Pintura Predial"))

        # Contato no topo direito
        canv.setFillColor(GRAY_L)
        canv.setFont("Helvetica", 7)
        contact = f"{company.get('phone','(11) 98765-4321')}  ·  {company.get('email','contato@pinturaperfeita.com')}"
        canv.drawRightString(w - MARGIN, h - 9*mm, contact)
        canv.drawRightString(w - MARGIN, h - 12.5*mm, company.get("website", "pinturaperfeita.com"))

        # Barra dourada fina
        canv.setFillColor(GOLD)
        canv.rect(0, h - 14*mm - 1.5, w, 1.5, fill=1, stroke=0)

        # ── Rodapé ──
        canv.setFillColor(BLACK)
        canv.rect(0, 0, w, 10*mm, fill=1, stroke=0)

        # Linha dourada acima do rodapé
        canv.setFillColor(GOLD)
        canv.rect(0, 10*mm, w, 0.8, fill=1, stroke=0)

        # Texto do rodapé
        canv.setFillColor(GRAY)
        canv.setFont("Helvetica", 6.5)
        footer_left = f"{company.get('name','Pintura Perfeita')} · CNPJ {company.get('cnpj','12.345.678/0001-90')} · {company.get('address','São Paulo, SP')}"
        canv.drawString(MARGIN, 5.5*mm, footer_left)

        # Número de página
        canv.setFillColor(GOLD)
        canv.setFont("Helvetica-Bold", 7)
        canv.drawRightString(w - MARGIN, 5.5*mm, f"Página {doc.page}")

        canv.restoreState()

    return _draw


# ─── Estilos tipográficos ─────────────────────────────────────

def build_styles():
    return {
        "title": ParagraphStyle("title",
            fontName="Helvetica-Bold", fontSize=24, textColor=BLACK,
            leading=28, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle",
            fontName="Helvetica", fontSize=10, textColor=GRAY,
            leading=14, spaceAfter=2),
        "section": ParagraphStyle("section",
            fontName="Helvetica-Bold", fontSize=8, textColor=GOLD,
            leading=12, spaceBefore=12, spaceAfter=6,
            textTransform="uppercase", letterSpacing=1.2),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#3F3F46"),
            leading=14, spaceAfter=4),
        "body_dark": ParagraphStyle("body_dark",
            fontName="Helvetica", fontSize=9, textColor=BLACK,
            leading=14, spaceAfter=4),
        "small": ParagraphStyle("small",
            fontName="Helvetica", fontSize=7.5, textColor=GRAY,
            leading=11),
        "label": ParagraphStyle("label",
            fontName="Helvetica-Bold", fontSize=7, textColor=GRAY,
            leading=10, textTransform="uppercase"),
        "value": ParagraphStyle("value",
            fontName="Helvetica-Bold", fontSize=10, textColor=BLACK,
            leading=13),
        "value_gold": ParagraphStyle("value_gold",
            fontName="Helvetica-Bold", fontSize=11, textColor=GOLD,
            leading=14),
        "total_label": ParagraphStyle("total_label",
            fontName="Helvetica-Bold", fontSize=14, textColor=WHITE,
            leading=18),
        "total_value": ParagraphStyle("total_value",
            fontName="Helvetica-Bold", fontSize=22, textColor=GOLD,
            leading=26),
        "code": ParagraphStyle("code",
            fontName="Courier-Bold", fontSize=9, textColor=GOLD,
            leading=12),
        "highlight": ParagraphStyle("highlight",
            fontName="Helvetica-Bold", fontSize=9, textColor=BLACK,
            leading=13, backColor=GOLD_BG),
        "obs": ParagraphStyle("obs",
            fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#52525B"),
            leading=13, leftIndent=8),
        "white": ParagraphStyle("white",
            fontName="Helvetica", fontSize=8, textColor=WHITE, leading=12),
        "white_bold": ParagraphStyle("white_bold",
            fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, leading=13),
    }


# ─── Funções auxiliares ───────────────────────────────────────

def fmt_brl(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_date(d) -> str:
    if isinstance(d, str):
        try: d = datetime.fromisoformat(d)
        except: return d
    if isinstance(d, (datetime, date)):
        return d.strftime("%d/%m/%Y")
    return str(d)

def info_cell(label: str, value: str, styles: dict, bg=None) -> Table:
    """Célula de informação label + valor empilhados."""
    data = [
        [Paragraph(label.upper(), styles["label"])],
        [Paragraph(value or "—", styles["value"])],
    ]
    t = Table(data, colWidths=["100%"])
    ts = [
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]
    if bg:
        ts.append(("BACKGROUND", (0,0), (-1,-1), bg))
    t.setStyle(TableStyle(ts))
    return t

def badge_text(text: str, color=GOLD) -> str:
    """Retorna texto com estilo de badge para Paragraph."""
    return f'<font color="#{color.hexval()[1:]}" size="8"><b> {text.upper()} </b></font>'


# ─── GERADOR PRINCIPAL ────────────────────────────────────────

def generate_proposal_pdf(estimate: dict, output_path: str) -> str:
    """
    Gera o PDF completo da proposta comercial.
    
    Args:
        estimate: Dicionário com todos os dados do orçamento
        output_path: Caminho para salvar o arquivo .pdf
    
    Returns:
        Caminho do arquivo gerado
    """
    # Extrair dados
    company  = estimate.get("company", {})
    client   = estimate.get("client", {})
    calc     = estimate.get("calc", {})
    form     = estimate.get("form", {})
    code     = estimate.get("code", "PP-XXXXXX")
    items    = estimate.get("items", [])
    ai_desc  = estimate.get("ai_description", "")
    created  = estimate.get("created_at", datetime.now().isoformat())

    S = build_styles()

    # Configurar documento
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18*mm,
        bottomMargin=14*mm,
        title=f"Proposta {code} — {client.get('name','Cliente')}",
        author=company.get("name", "Pintura Perfeita"),
        subject="Proposta Comercial de Pintura",
        creator="Pintura Perfeita Pro System",
    )

    story = []
    header_footer = make_header_footer(company)

    # ═══════════════════════════════════════════════════════════
    # PÁGINA 1 — CAPA / HEADER DA PROPOSTA
    # ═══════════════════════════════════════════════════════════

    story.append(Spacer(1, 6*mm))

    # ── Linha de identificação do documento ──
    id_data = [[
        Paragraph("PROPOSTA COMERCIAL", ParagraphStyle("pc", fontName="Helvetica", fontSize=8, textColor=GRAY, letterSpacing=2)),
        Paragraph(f'<font color="#C9A84C"><b>{code}</b></font>', ParagraphStyle("cd", fontName="Courier-Bold", fontSize=14, textColor=GOLD, alignment=TA_RIGHT)),
    ]]
    id_table = Table(id_data, colWidths=[CONTENT_W*0.6, CONTENT_W*0.4])
    id_table.setStyle(TableStyle([
        ("ALIGN",  (0,0), (0,0), "LEFT"),
        ("ALIGN",  (1,0), (1,0), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(id_table)
    story.append(GoldDivider(CONTENT_W))
    story.append(Spacer(1, 4*mm))

    # ── Título + data de emissão ──
    title_data = [[
        Paragraph(f"Proposta para<br/><b>{client.get('name','Cliente')}</b>",
                  ParagraphStyle("ptitle", fontName="Helvetica-Bold", fontSize=20, textColor=BLACK, leading=26)),
        Paragraph(
            f'<font color="#71717A" size="8">Emissão</font><br/>'
            f'<b>{fmt_date(created)}</b><br/>'
            f'<font color="#71717A" size="8">Validade</font><br/>'
            f'<b>{estimate.get("validity_days", 30)} dias</b>',
            ParagraphStyle("pdate", fontName="Helvetica", fontSize=10, textColor=BLACK, alignment=TA_RIGHT, leading=14)
        ),
    ]]
    title_tbl = Table(title_data, colWidths=[CONTENT_W*0.65, CONTENT_W*0.35])
    title_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Grid de informações: Cliente + Imóvel ──
    prop_type_map = {
        "casa_residencial": "Casa Residencial",
        "apartamento": "Apartamento",
        "condominio": "Condomínio",
        "bloco_residencial": "Bloco Residencial",
        "mansao": "Mansão",
        "comercial": "Imóvel Comercial",
        "escritorio": "Escritório",
        "galpao": "Galpão Industrial",
    }
    prop_type = prop_type_map.get(form.get("propertyType",""), form.get("propertyType",""))

    info_cells_left = [
        ["CLIENTE", client.get("name", "—")],
        ["TELEFONE / WHATSAPP", client.get("phone", "—")],
        ["E-MAIL", client.get("email", "—")],
        ["CIDADE", client.get("city", "—")],
    ]
    info_cells_right = [
        ["TIPO DE IMÓVEL", prop_type],
        ["ÁREA TOTAL", f"{form.get('totalArea', 0)}m²"],
        ["ESTADO DAS PAREDES", form.get("wallCondition", "").capitalize()],
        ["ENDEREÇO DA OBRA", estimate.get("property_address", "—")],
    ]

    def make_info_block(cells, bg=LIGHT_BG):
        rows = []
        for label, value in cells:
            rows.append([
                Paragraph(label, S["label"]),
                Paragraph(str(value), S["body_dark"]),
            ])
        t = Table(rows, colWidths=[CONTENT_W*0.22, CONTENT_W*0.28])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg),
            ("ALIGN", (0,0), (0,-1), "LEFT"),
            ("ALIGN", (1,0), (1,-1), "LEFT"),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("LINEBELOW", (0,0), (-1,-2), 0.3, BORDER),
            ("ROUNDEDCORNERS", [4]),
        ]))
        return t

    info_row = [[make_info_block(info_cells_left), Spacer(4*mm, 1), make_info_block(info_cells_right, GOLD_BG)]]
    info_table = Table(info_row, colWidths=[CONTENT_W*0.5, 4*mm, CONTENT_W*0.5])
    info_table.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5*mm))

    # ── Serviços inclusos (checkboxes visuais) ──
    story.append(Paragraph("ESCOPO DOS SERVIÇOS", S["section"]))

    services = [
        ("has_internal",      "✓ Pintura Interna",     form.get("hasInternal")),
        ("has_external",      "✓ Pintura Externa",     form.get("hasExternal")),
        ("has_ceiling",       "✓ Pintura de Tetos",    form.get("hasCeiling")),
        ("has_massa_corrida", "✓ Massa Corrida",        form.get("hasMassaCorrida")),
        ("has_texture",       "✓ Textura / Grafiato",  form.get("hasTexture")),
        ("has_facade",        "✓ Fachada",              form.get("hasFacade")),
        ("has_walls",         "✓ Muros Externos",       form.get("hasWalls")),
    ]
    active = [s[1] for s in services if s[2]]
    inactive = [s[1].replace("✓", "○") for s in services if not s[2]]

    paint_map = {
        "economica": "PVA Econômica",
        "standard":  "Acrílica Standard",
        "premium":   "Acrílica Premium",
        "luxo":      "Látex Semibrilho",
        "textura":   "Textura Acrílica",
        "epoxy":     "Epóxi Industrial",
    }

    # Tabela de serviços em 3 colunas
    svc_items = active + [f"  Tinta: {paint_map.get(form.get('paintType',''),'Standard')}",
                          f"  {form.get('numCoats',2)}x Demãos", f"  Garantia: {estimate.get('warranty','1 ano')}"]
    cols = 3
    rows_svc = [svc_items[i:i+cols] for i in range(0, len(svc_items), cols)]
    if rows_svc and len(rows_svc[-1]) < cols:
        rows_svc[-1] += [""] * (cols - len(rows_svc[-1]))

    svc_styled = []
    for row in rows_svc:
        svc_styled.append([
            Paragraph(cell, ParagraphStyle("svc", fontName="Helvetica",
                fontSize=8.5, textColor=GREEN if cell.startswith("✓") else colors.HexColor("#52525B"),
                leading=12))
            for cell in row
        ])
    col_w = CONTENT_W / cols
    svc_tbl = Table(svc_styled, colWidths=[col_w]*cols)
    svc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("LINEBELOW", (0,0), (-1,-2), 0.3, BORDER),
    ]))
    story.append(svc_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Descrição técnica (IA) ──
    if ai_desc:
        story.append(Paragraph("DESCRIÇÃO TÉCNICA DA OBRA", S["section"]))
        story.append(Paragraph(ai_desc, S["obs"]))
        story.append(Spacer(1, 3*mm))

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 2 — MATERIAIS DETALHADOS
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("MATERIAIS E INSUMOS", S["section"]))

    mat_data = [
        ["ITEM", "DESCRIÇÃO", "QTD.", "UNIT.", "VALOR"],
    ]

    paint_labels = {
        "economica": "Tinta PVA Econômica",
        "standard":  "Tinta Acrílica Standard Suvinil",
        "premium":   "Tinta Acrílica Premium Coral",
        "luxo":      "Tinta Látex Semibrilho",
        "textura":   "Textura Acrílica Quartzolit",
        "epoxy":     "Tinta Epóxi Industrial",
    }
    paint_name = paint_labels.get(form.get("paintType","standard"), "Tinta Acrílica")

    mat_rows = [
        (paint_name, f"{calc.get('paintLiters',0):.0f}", "litros", calc.get("paintCost",0)),
    ]
    if form.get("hasMassaCorrida"):
        mat_rows.append(("Massa Corrida PVA", f"{calc.get('massaKg',0):.0f}", "kg", calc.get("massaCost",0)))
    mat_rows += [
        ("Selador / Fundo Preparador", f"{calc.get('seladorL',0):.0f}", "litros", calc.get("seladorCost",0)),
        ("Rolos, Pincéis e Ferramentas", f"{calc.get('rolos',0)}", "unid.", calc.get("rolos",0)*18),
        ("Fitas, Lixas e Plásticos Proteção", "—", "kits", calc.get("miscCost",0) - calc.get("rolos",0)*18),
    ]

    for i, (desc, qty, unit, val) in enumerate(mat_rows, 1):
        mat_data.append([
            str(i), desc, qty, unit, fmt_brl(max(0, val))
        ])

    mat_data.append(["", "", "", "SUBTOTAL MATERIAIS", fmt_brl(calc.get("materialsCost",0))])

    mat_col_w = [10*mm, CONTENT_W - 10*mm - 18*mm - 14*mm - 30*mm, 18*mm, 14*mm, 30*mm]
    mat_tbl = Table(mat_data, colWidths=mat_col_w, repeatRows=1)
    mat_tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0,0), (-1,0), BLACK),
        ("TEXTCOLOR",     (0,0), (-1,0), GOLD),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 7.5),
        ("TOPPADDING",    (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 7),
        ("LETTERSPACINGPADDING", (0,0), (-1,0), 1),
        # Body alternado
        *[("BACKGROUND", (0,i), (-1,i), LIGHT_BG if i%2==1 else colors.white)
          for i in range(1, len(mat_data)-1)],
        # Subtotal row
        ("BACKGROUND", (0,-1), (-1,-1), DARK_BG),
        ("FONTNAME",   (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (3,-1), (-1,-1), GOLD),
        ("FONTSIZE",   (3,-1), (-1,-1), 8),
        # Alinhamentos
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (2,0), (2,-1), "CENTER"),
        ("ALIGN", (3,0), (4,-1), "RIGHT"),
        ("FONTSIZE",      (0,1), (-1,-1), 8.5),
        ("TOPPADDING",    (0,1), (-1,-1), 5),
        ("BOTTOMPADDING", (0,1), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("LINEBELOW",     (0,0), (-1,0),  0.5, GOLD),
        ("LINEBELOW",     (0,1), (-1,-2), 0.3, BORDER),
        ("LINEABOVE",     (0,-1), (-1,-1), 0.5, GOLD_DIM),
    ]))
    story.append(mat_tbl)
    story.append(Spacer(1, 4*mm))

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 3 — MÃO DE OBRA
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("MÃO DE OBRA", S["section"]))

    labor_data = [
        ["PROFISSIONAL", "QTDE.", "DIÁRIAS", "R$/DIÁRIA", "SUBTOTAL"],
        ["Pintor(es)", str(calc.get("numWorkers",1)), str(calc.get("workDays",1)),
         fmt_brl(form.get("workerDailyRate",280)),
         fmt_brl(calc.get("numWorkers",1) * calc.get("workDays",1) * form.get("workerDailyRate",280))],
        ["Ajudante(s)", str(calc.get("numHelpers",0)), str(calc.get("workDays",1)),
         fmt_brl(form.get("helperDailyRate",180)),
         fmt_brl(calc.get("numHelpers",0) * calc.get("workDays",1) * form.get("helperDailyRate",180))],
        ["", "", "", "TOTAL MÃO DE OBRA", fmt_brl(calc.get("laborCost",0))],
    ]
    lab_col_w = [CONTENT_W*0.3, CONTENT_W*0.12, CONTENT_W*0.14, CONTENT_W*0.22, CONTENT_W*0.22]
    lab_tbl = Table(labor_data, colWidths=lab_col_w, repeatRows=1)
    lab_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), BLACK),
        ("TEXTCOLOR",     (0,0), (-1,0), GOLD),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 7.5),
        ("TOPPADDING",    (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 7),
        ("BACKGROUND", (0,1), (-1,1), LIGHT_BG),
        ("BACKGROUND", (0,2), (-1,2), colors.white),
        ("BACKGROUND", (0,-1), (-1,-1), DARK_BG),
        ("FONTNAME",   (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (3,-1), (-1,-1), GOLD),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("ALIGN", (3,0), (4,-1), "RIGHT"),
        ("ALIGN", (3,-1), (4,-1), "RIGHT"),
        ("FONTSIZE",      (0,1), (-1,-1), 8.5),
        ("TOPPADDING",    (0,1), (-1,-1), 6),
        ("BOTTOMPADDING", (0,1), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("LINEBELOW", (0,0), (-1,0), 0.5, GOLD),
        ("LINEBELOW", (0,1), (-1,-2), 0.3, BORDER),
        ("LINEABOVE", (0,-1), (-1,-1), 0.5, GOLD_DIM),
    ]))
    story.append(lab_tbl)
    story.append(Spacer(1, 5*mm))

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 4 — RESUMO FINANCEIRO (destaque visual)
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("RESUMO FINANCEIRO", S["section"]))

    fin_rows_data = [
        ("Subtotal Materiais",        calc.get("materialsCost", 0), colors.white),
        ("Subtotal Mão de Obra",      calc.get("laborCost", 0),     colors.white),
        ("Subtotal",                  calc.get("subtotal", 0),       LIGHT_BG),
        (f"Margem Operacional ({form.get('profitMargin',30):.0f}%)", calc.get("profit",0), GOLD_BG),
    ]

    fin_data = []
    for label, val, bg in fin_rows_data:
        fin_data.append([
            Paragraph(label, ParagraphStyle("fl", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#52525B"))),
            Paragraph(fmt_brl(val), ParagraphStyle("fv", fontName="Helvetica-Bold", fontSize=9, textColor=BLACK, alignment=TA_RIGHT)),
        ])

    # Linha do total
    fin_data.append([
        Paragraph("VALOR TOTAL DA PROPOSTA", ParagraphStyle("tl", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE)),
        Paragraph(fmt_brl(calc.get("total",0)), ParagraphStyle("tv", fontName="Helvetica-Bold", fontSize=18, textColor=GOLD, alignment=TA_RIGHT)),
    ])
    fin_data.append([
        Paragraph(f"Equivalente a {fmt_brl(calc.get('pricePerM2',0))}/m²", S["small"]),
        Paragraph("", S["small"]),
    ])

    fin_col_w = [CONTENT_W*0.6, CONTENT_W*0.4]
    fin_tbl = Table(fin_data, colWidths=fin_col_w)
    fin_bg_styles = [
        ("BACKGROUND", (0,i), (-1,i), bg)
        for i, (_, __, bg) in enumerate(fin_rows_data)
    ]
    fin_tbl.setStyle(TableStyle([
        *fin_bg_styles,
        ("BACKGROUND", (0, len(fin_rows_data)), (-1, len(fin_rows_data)), BLACK),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#F9F9F7")),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("LINEBELOW", (0,0), (-1,-3), 0.4, BORDER),
        ("LINEABOVE", (0,len(fin_rows_data)), (-1,len(fin_rows_data)), 2, GOLD),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(fin_tbl)
    story.append(Spacer(1, 5*mm))

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 5 — CONDIÇÕES COMERCIAIS
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("CONDIÇÕES COMERCIAIS", S["section"]))

    cond_items = [
        ("💳 Forma de Pagamento",  estimate.get("payment_terms", "50% entrada + 50% conclusão")),
        ("🛡️ Garantia do Serviço", estimate.get("warranty", "1 ano")),
        ("📅 Prazo de Execução",   f"{calc.get('workDays',1)} dias úteis"),
        ("🔖 Validade da Proposta",f"{estimate.get('validity_days',30)} dias corridos"),
    ]

    cond_data = [[
        Paragraph(label.replace("💳","").replace("🛡️","").replace("📅","").replace("🔖","").strip(),
                  ParagraphStyle("cl", fontName="Helvetica-Bold", fontSize=7.5, textColor=GOLD, leading=11)),
        Paragraph(value, ParagraphStyle("cv", fontName="Helvetica", fontSize=9, textColor=BLACK, leading=12)),
    ] for label, value in cond_items]

    cond_tbl = Table(cond_data, colWidths=[CONTENT_W*0.3, CONTENT_W*0.7])
    cond_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_BG),
        *[("BACKGROUND", (0,i), (-1,i), GOLD_BG if i%2==0 else LIGHT_BG) for i in range(len(cond_data))],
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("LINEBELOW", (0,0), (-1,-2), 0.3, BORDER),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(cond_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Observações ──
    obs = estimate.get("observations") or form.get("observations", "")
    if obs:
        story.append(Paragraph("OBSERVAÇÕES", S["section"]))
        obs_block = Table([[Paragraph(obs, S["obs"])]], colWidths=[CONTENT_W])
        obs_block.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FFFDF5")),
            ("LEFTBORDERPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("LINEONNLEFT",   (0,0), (0,-1), 2, GOLD),
        ]))
        story.append(obs_block)
        story.append(Spacer(1, 4*mm))

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 6 — ASSINATURA + QR CODE
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("APROVAÇÃO E ASSINATURA", S["section"]))

    # Bloco de aceite
    aceite_text = (
        f"Eu, <b>{client.get('name','___________________')}</b>, "
        f"declaro estar de acordo com os termos e condições desta proposta de prestação de serviços "
        f"de pintura no valor de <b>{fmt_brl(calc.get('total',0))}</b>, "
        f"conforme especificado neste documento (Proposta {code})."
    )
    story.append(Paragraph(aceite_text, ParagraphStyle(
        "aceite", fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#52525B"),
        leading=13, borderColor=BORDER, borderWidth=0.5, borderPadding=8,
        backColor=LIGHT_BG
    )))
    story.append(Spacer(1, 6*mm))

    # Grid de assinaturas + QR
    sig_data = [[
        [
            SignatureLine(CONTENT_W*0.45, client.get("name","Cliente"),
                         f"CPF/CNPJ: {client.get('document','_______________')}"),
            SignatureLine(CONTENT_W*0.45, company.get("name","Empresa"), "Responsável Técnico"),
        ],
        [
            Paragraph("LOCAL E DATA", S["label"]),
            SignatureLine(CONTENT_W*0.45),
            Paragraph("Aprovação online via QR Code:", S["small"]),
            QRCodeBox(45, f"pinturaperfeita.com/p/{code}"),
        ],
    ]]
    # Usar tabela simples em duas colunas para as assinaturas
    sig_left = Table(
        [[SignatureLine(CONTENT_W*0.44, client.get("name","Cliente"), f"CPF/CNPJ: {client.get('document','_______________')}")],
         [Spacer(1,4*mm)],
         [SignatureLine(CONTENT_W*0.44, company.get("name","Empresa"), "Responsável Técnico")]],
        colWidths=[CONTENT_W*0.44]
    )
    sig_left.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))

    sig_right = Table(
        [[Paragraph("LOCAL E DATA", S["label"])],
         [Spacer(1,2*mm)],
         [SignatureLine(CONTENT_W*0.44)],
         [Spacer(1,5*mm)],
         [Paragraph("Aprovação online via QR Code:", S["small"])],
         [Spacer(1,2*mm)],
         [QRCodeBox(45, f"pp/{code}")]],
        colWidths=[CONTENT_W*0.44]
    )
    sig_right.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))

    sig_outer = [[sig_left, Spacer(CONTENT_W*0.05, 1), sig_right]]
    sig_tbl = Table(sig_outer, colWidths=[CONTENT_W*0.47, CONTENT_W*0.05, CONTENT_W*0.47])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    story.append(sig_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Faixa de garantia e certificação ──
    cert_data = [[
        Paragraph("✓  EMPRESA CERTIFICADA", ParagraphStyle("cert", fontName="Helvetica-Bold", fontSize=8, textColor=GOLD, letterSpacing=1)),
        Paragraph("✓  MATERIAIS DE PRIMEIRA LINHA", ParagraphStyle("cert", fontName="Helvetica-Bold", fontSize=8, textColor=GOLD, letterSpacing=1)),
        Paragraph("✓  GARANTIA INCLUSA", ParagraphStyle("cert", fontName="Helvetica-Bold", fontSize=8, textColor=GOLD, letterSpacing=1)),
        Paragraph("✓  EQUIPE TREINADA", ParagraphStyle("cert", fontName="Helvetica-Bold", fontSize=8, textColor=GOLD, letterSpacing=1)),
    ]]
    cert_tbl = Table(cert_data, colWidths=[CONTENT_W/4]*4)
    cert_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), BLACK),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(cert_tbl)

    # ─── Build ───────────────────────────────────────────────
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return output_path


# ─── Função de conveniência ───────────────────────────────────

def generate_from_dict(data: dict, output_path: str) -> str:
    """Wrapper para usar direto com dicionário Python."""
    return generate_proposal_pdf(data, output_path)


def generate_from_json(json_str: str, output_path: str) -> str:
    """Wrapper para usar com JSON (ex: chamada de API)."""
    data = json.loads(json_str)
    return generate_proposal_pdf(data, output_path)
