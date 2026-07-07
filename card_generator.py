import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from qr_code import gerar_qrcode_png


CARD_LARGURA = 1080
CARD_ALTURA = 1350
FOTO_TAMANHO = 720
QR_TAMANHO = 240

COR_FUNDO = "#060f0a"
COR_MATRIX = "#00ff41"
COR_MATRIX_CLARO = "#39ff8a"
COR_TEXTO = "#f4f4f5"
COR_TEXTO_SECUNDARIO = "#9ba39d"
COR_QR_BORDA = "#00ff41"


def carregar_fonte(tamanho: int, negrito: bool = False):
    """Carrega uma fonte disponível no projeto ou no sistema operacional."""
    nome_arquivo = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
    caminho_bundled = os.path.join(os.path.dirname(__file__), "assets", "fonts", nome_arquivo)

    nomes = [
        caminho_bundled,
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
    """Desenha um texto centralizado na largura informada e retorna sua altura."""
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    texto_largura = bbox[2] - bbox[0]
    x = (largura - texto_largura) // 2
    draw.text((x, y), texto, font=fonte, fill=cor)
    return bbox[3] - bbox[1]


def texto_bicolor_centralizado(draw: ImageDraw.ImageDraw, parte1: str, parte2: str, y: int, fonte, cor1: str, cor2: str, largura: int = CARD_LARGURA):
    """Desenha duas partes de texto centralizadas com cores diferentes."""
    bbox1 = draw.textbbox((0, 0), parte1, font=fonte)
    bbox2 = draw.textbbox((0, 0), parte2, font=fonte)
    largura_total = (bbox1[2] - bbox1[0]) + (bbox2[2] - bbox2[0])
    x = (largura - largura_total) // 2
    draw.text((x, y), parte1, font=fonte, fill=cor1)
    draw.text((x + (bbox1[2] - bbox1[0]), y), parte2, font=fonte, fill=cor2)


def quebrar_texto(draw: ImageDraw.ImageDraw, texto: str, fonte, largura_maxima: int) -> list[str]:
    """Quebra um texto em linhas respeitando a largura máxima informada."""
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


def ajustar_fonte_e_quebrar(
    draw: ImageDraw.ImageDraw,
    texto: str,
    tamanho_inicial: int,
    tamanho_minimo: int,
    largura_maxima: int,
    max_linhas: int = 2,
    negrito: bool = True,
):
    """Ajusta a fonte e quebra o texto para caber no limite de linhas."""
    tamanho = tamanho_inicial

    while tamanho >= tamanho_minimo:
        fonte = carregar_fonte(tamanho, negrito=negrito)
        linhas = quebrar_texto(draw, texto, fonte, largura_maxima)
        if len(linhas) <= max_linhas:
            return fonte, linhas
        tamanho -= 4

    fonte = carregar_fonte(tamanho_minimo, negrito=negrito)
    linhas = quebrar_texto(draw, texto, fonte, largura_maxima)[:max_linhas]
    return fonte, linhas


def gerar_card_jpg(lead, foto_bytes: bytes, url_download: str) -> bytes:
    """Gera o card personalizado do lead em formato JPG."""
    try:
        foto = Image.open(BytesIO(foto_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("Foto do lead nao e uma imagem valida") from exc

    # Draw "de medicao": metricas de fonte independem do tamanho do canvas,
    # entao usamos um draw descartavel pra calcular tudo ANTES de saber a
    # altura final do card. Isso garante que nome/cargo longos nunca colidam
    # com o QR code, em vez de depender de coordenadas fixas no chute.
    medidor = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    fonte_marca = carregar_fonte(40, negrito=True)
    fonte_titulo = carregar_fonte(26)
    fonte_rodape = carregar_fonte(24)
    titulo = os.getenv("CARD_EVENT_TITLE", "Meu Card")

    foto_x = (CARD_LARGURA - FOTO_TAMANHO) // 2
    foto_y = 190
    foto_bottom = foto_y + FOTO_TAMANHO

    nome = lead.nome or "Participante"
    fonte_nome, linhas_nome = ajustar_fonte_e_quebrar(
        medidor, nome, tamanho_inicial=52, tamanho_minimo=28, largura_maxima=940, max_linhas=2, negrito=True
    )

    detalhes = [d for d in (lead.cargo, lead.empresa, lead.setor) if d]
    detalhe_texto = " | ".join(detalhes) if detalhes else (lead.cidade or "")

    fonte_detalhe, linhas_detalhe = (None, [])
    if detalhe_texto:
        fonte_detalhe, linhas_detalhe = ajustar_fonte_e_quebrar(
            medidor, detalhe_texto, tamanho_inicial=28, tamanho_minimo=18, largura_maxima=900, max_linhas=1, negrito=False
        )

    # Simula o desenho do bloco de texto pra descobrir onde ele termina.
    y_atual = foto_bottom + 50
    for linha in linhas_nome:
        bbox = medidor.textbbox((0, 0), linha, font=fonte_nome)
        y_atual += (bbox[3] - bbox[1]) + 18
    for linha in linhas_detalhe:
        bbox = medidor.textbbox((0, 0), linha, font=fonte_detalhe)
        y_atual += (bbox[3] - bbox[1]) + 8

    qr_y = y_atual + 40
    qr_bottom = qr_y + QR_TAMANHO + 24
    rodape_y = qr_bottom + 30
    card_altura = max(CARD_ALTURA, rodape_y + 50)

    card = Image.new("RGB", (CARD_LARGURA, card_altura), COR_FUNDO)
    draw = ImageDraw.Draw(card)

    # --- Cabecalho: marca "PicCapture" + titulo do evento ---
    texto_bicolor_centralizado(draw, "Pic", "Capture", 44, fonte_marca, COR_TEXTO, COR_MATRIX)
    texto_centralizado(draw, titulo, 96, fonte_titulo, COR_TEXTO_SECUNDARIO)
    draw.line((90, 150, CARD_LARGURA - 90, 150), fill="#1a2b22", width=2)

    # --- Foto (ja vem com a moldura aplicada pelo frontend, sem contorno extra aqui) ---
    foto = ImageOps.fit(foto, (FOTO_TAMANHO, FOTO_TAMANHO), method=Image.Resampling.LANCZOS)
    card.paste(foto, (foto_x, foto_y))

    # --- Nome e dados do lead ---
    y_desenho = foto_bottom + 50
    for linha in linhas_nome:
        altura_linha = texto_centralizado(draw, linha, y_desenho, fonte_nome, COR_TEXTO)
        y_desenho += altura_linha + 18

    for linha in linhas_detalhe:
        altura_linha = texto_centralizado(draw, linha, y_desenho, fonte_detalhe, COR_MATRIX_CLARO)
        y_desenho += altura_linha + 8

    # --- QR code (fundo branco mantido de proposito, garante leitura pelo scanner) ---
    qrcode = Image.open(gerar_qrcode_png(url_download)).convert("RGB")
    qrcode = qrcode.resize((QR_TAMANHO, QR_TAMANHO), Image.Resampling.LANCZOS)
    qr_x = (CARD_LARGURA - QR_TAMANHO) // 2

    draw.rounded_rectangle(
        (qr_x - 12, qr_y - 12, qr_x + QR_TAMANHO + 12, qr_y + QR_TAMANHO + 12),
        radius=18,
        fill="#ffffff",
        outline=COR_QR_BORDA,
        width=3,
    )
    card.paste(qrcode, (qr_x, qr_y))
    texto_centralizado(draw, "Escaneie para baixar seu card", rodape_y, fonte_rodape, COR_TEXTO_SECUNDARIO)

    buffer = BytesIO()
    card.save(buffer, format="JPEG", quality=92, optimize=True)

    return buffer.getvalue()
