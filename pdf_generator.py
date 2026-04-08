"""Generate rental contract PDF using reportlab."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
import models

_FONT_REGISTERED = False

def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return "DejaVu"
    paths = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for reg, bold in paths:
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", reg))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold))
            _FONT_REGISTERED = True
            return "DejaVu"
        except Exception:
            pass
    return "Helvetica"


def generate(contract: models.RentalContract) -> bytes:
    font = _register_fonts()
    font_bold = font + ("-Bold" if font == "DejaVu" else "-Bold")

    owner = contract.owner
    renter = contract.renter
    apt = contract.apartment

    owner_name = owner.username if owner else "—"
    owner_phone = owner.phone_number or "не указан"
    renter_name = renter.username if renter else "—"
    renter_phone = renter.phone_number or "не указан"
    apt_title = apt.title if apt else "—"
    apt_address = f"{apt.city}, {apt.address}" if apt else "—"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", fontName=font_bold, fontSize=14,
                                  spaceAfter=4, alignment=1)
    center_style = ParagraphStyle("center", fontName=font, fontSize=10,
                                   spaceAfter=2, alignment=1)
    heading_style = ParagraphStyle("heading", fontName=font_bold, fontSize=11,
                                    spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle("body", fontName=font, fontSize=10,
                                 spaceAfter=4, leading=15)
    sig_label_style = ParagraphStyle("sig_label", fontName=font_bold, fontSize=10,
                                      spaceAfter=2)
    sig_body_style = ParagraphStyle("sig_body", fontName=font, fontSize=10,
                                     spaceAfter=2)

    story = []

    story.append(Paragraph("ДОГОВОР АРЕНДЫ ЖИЛОГО ПОМЕЩЕНИЯ", title_style))
    story.append(Paragraph(f"№ {contract.contract_number}", center_style))
    story.append(Paragraph(f"Дата: {contract.created_at.strftime('%d.%m.%Y')}", center_style))
    story.append(Spacer(1, 8*mm))

    def section(title, body):
        story.append(Paragraph(title, heading_style))
        story.append(Paragraph(body.replace("\n", "<br/>"), body_style))

    section(
        "1. СТОРОНЫ ДОГОВОРА",
        f"Арендодатель: {owner_name}, тел.: {owner_phone}\n"
        f"Арендатор: {renter_name}, тел.: {renter_phone}"
    )
    section(
        "2. ПРЕДМЕТ ДОГОВОРА",
        f"Объект аренды: {apt_title}\n"
        f"Адрес: {apt_address}\n"
        f"Срок аренды: {contract.start_date.strftime('%d.%m.%Y')} — {contract.end_date.strftime('%d.%m.%Y')}\n"
        f"Ежемесячная плата: {float(contract.monthly_price):,.0f} руб."
    )
    section(
        "3. ПРАВА И ОБЯЗАННОСТИ СТОРОН",
        "3.1. Арендатор обязуется использовать помещение для проживания, своевременно вносить арендную плату.\n"
        "3.2. Арендодатель обязуется передать помещение в пригодном для проживания состоянии."
    )
    section(
        "4. ОТВЕТСТВЕННОСТЬ СТОРОН",
        "4.1. При досрочном расторжении договора сторона-инициатор обязана уведомить другую сторону за 30 дней."
    )
    section(
        "5. ПРОЧИЕ УСЛОВИЯ",
        "5.1. Договор составлен в двух экземплярах.\n"
        "5.2. Все изменения действительны только в письменном виде."
    )

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("ПОДПИСИ СТОРОН", heading_style))
    story.append(Spacer(1, 4*mm))

    def sig_block(label, name, phone, sig_data, signed_at):
        items = [Paragraph(label, sig_label_style),
                 Paragraph(name, sig_body_style),
                 Paragraph(phone, sig_body_style)]
        if sig_data:
            try:
                img = PILImage.open(io.BytesIO(sig_data)).convert("RGBA")
                img_buf = io.BytesIO()
                img.save(img_buf, format="PNG")
                img_buf.seek(0)
                items.append(RLImage(img_buf, width=60*mm, height=20*mm))
                if signed_at:
                    items.append(Paragraph(
                        f"Подписано: {signed_at.strftime('%d.%m.%Y %H:%M')}",
                        ParagraphStyle("small", fontName=font, fontSize=8)))
            except Exception:
                items.append(Paragraph("_______________________", sig_body_style))
        else:
            items.append(Paragraph("_______________________", sig_body_style))
        return items

    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    owner_col = sig_block("Арендодатель:", owner_name, owner_phone,
                           contract.owner_signature_data, contract.owner_signed_at)
    renter_col = sig_block("Арендатор:", renter_name, renter_phone,
                            contract.signature_data, contract.signed_at)

    max_rows = max(len(owner_col), len(renter_col))
    while len(owner_col) < max_rows:
        owner_col.append(Spacer(1, 1))
    while len(renter_col) < max_rows:
        renter_col.append(Spacer(1, 1))

    col_w = (A4[0] - 40*mm) / 2
    table_data = [[owner_col[i], renter_col[i]] for i in range(max_rows)]
    tbl = Table(table_data, colWidths=[col_w, col_w])
    tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(tbl)

    doc.build(story)
    return buf.getvalue()
