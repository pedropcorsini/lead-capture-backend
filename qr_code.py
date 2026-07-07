from io import BytesIO

import qrcode


def gerar_qrcode_png(conteudo: str) -> BytesIO:
    """Gera um QR Code em PNG para o conteúdo informado."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(conteudo)
    qr.make(fit=True)

    imagem = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer
