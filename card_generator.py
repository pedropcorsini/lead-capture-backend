import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from qr_code import gerar_qrcode_png


CARD_LARGURA = 1080
CARD_ALTURA = 1350
FOTO_TAMANHO = 720
QR_TAMANHO = 170


def carregar_fonte(tamanho: int, negrito: bool = False):
    nomes = [
        "arialbd.ttf" if negrito else "arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if negrito else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for nome in nomes:
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue

    return ImageFont.load_default()


def texto_centralizado(draw: ImageDraw.ImageDraw, texto: str, y: int, fonte, cor: str, largura: int = CARD_LARGURA):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    texto_largura = bbox[2] - bbox[0]
    x = (largura - texto_largura) // 2
    draw.text((x, y), texto, font=fonte, fill=cor)


def quebrar_texto(draw: ImageDraw.ImageDraw, texto: str, fonte, largura_maxima: int) -> list[str]:
    palavras = texto.split()
    linhas = []
    linha_atual = ""

    for palavra in palavras:
        candidata = f"{linha_atual} {palavra}".strip()
        bbox = draw.textbbox((0, 0), candidata, font=fonte)

        if bbox[2] - bbox[0] <= largura_maxima:
            linha_atual = candidata
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra

    if linha_atual:
        linhas.append(linha_atual)

    return linhas


def gerar_card_jpg(lead, foto_bytes: bytes, url_download: str) -> bytes:
    try:
        foto = Image.open(BytesIO(foto_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("Foto do lead nao e uma imagem valida") from exc

    card = Image.new("RGB", (CARD_LARGURA, CARD_ALTURA), "#f7f3ec")
    draw = ImageDraw.Draw(card)

    fonte_titulo = carregar_fonte(46, negrito=True)
    fonte_nome = carregar_fonte(54, negrito=True)
    fonte_info = carregar_fonte(30)
    fonte_info_negrito = carregar_fonte(32, negrito=True)
    fonte_rodape = carregar_fonte(25)

    cor_primaria = "#10233f"
    cor_texto = "#18202a"
    cor_secundaria = "#5f6673"

    draw.rectangle((0, 0, CARD_LARGURA, 150), fill=cor_primaria)
    titulo = os.getenv("CARD_EVENT_TITLE", "Meu Card")
    texto_centralizado(draw, titulo, 48, fonte_titulo, "#ffffff")

    foto = ImageOps.fit(foto, (FOTO_TAMANHO, FOTO_TAMANHO), method=Image.Resampling.LANCZOS)
    foto_x = (CARD_LARGURA - FOTO_TAMANHO) // 2
    foto_y = 180

    draw.rounded_rectangle(
        (foto_x - 18, foto_y - 18, foto_x + FOTO_TAMANHO + 18, foto_y + FOTO_TAMANHO + 18),
        radius=34,
        fill="#ffffff",
        outline="#e7dfd2",
        width=3,
    )
    card.paste(foto, (foto_x, foto_y))

    nome = lead.nome or "Participante"
    linhas_nome = quebrar_texto(draw, nome, fonte_nome, 900)[:2]
    y_atual = 935

    for linha in linhas_nome:
        texto_centralizado(draw, linha, y_atual, fonte_nome, cor_texto)
        y_atual += 62

    detalhes = []

    if lead.cargo:
        detalhes.append(lead.cargo)

    if lead.empresa:
        detalhes.append(lead.empresa)

    if lead.setor:
        detalhes.append(lead.setor)

    if detalhes:
        detalhe_texto = " | ".join(detalhes)
        linhas_detalhe = quebrar_texto(draw, detalhe_texto, fonte_info, 860)[:2]

        for linha in linhas_detalhe:
            texto_centralizado(draw, linha, y_atual + 4, fonte_info, cor_secundaria)
            y_atual += 40
    else:
        texto_centralizado(draw, lead.cidade or "", y_atual + 4, fonte_info, cor_secundaria)
        y_atual += 40

    qrcode = Image.open(gerar_qrcode_png(url_download)).convert("RGB")
    qrcode = qrcode.resize((QR_TAMANHO, QR_TAMANHO), Image.Resampling.LANCZOS)
    qr_x = (CARD_LARGURA - QR_TAMANHO) // 2
    qr_y = 1128

    draw.rounded_rectangle(
        (qr_x - 12, qr_y - 12, qr_x + QR_TAMANHO + 12, qr_y + QR_TAMANHO + 12),
        radius=18,
        fill="#ffffff",
        outline="#e7dfd2",
        width=2,
    )
    card.paste(qrcode, (qr_x, qr_y))
    texto_centralizado(draw, "Escaneie para baixar seu card", 1314, fonte_rodape, cor_secundaria)

    buffer = BytesIO()
    card.save(buffer, format="JPEG", quality=92, optimize=True)

    return buffer.getvalue()
