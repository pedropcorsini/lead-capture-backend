import os
import re
from typing import Optional

from fastapi import HTTPException, UploadFile


MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024


def apenas_digitos(valor: str) -> str:
    return re.sub(r"\D", "", str(valor))


def normalizar_texto_obrigatorio(valor: str, nome_campo: str) -> str:
    if valor is None:
        raise ValueError(f"{nome_campo} e obrigatorio")

    texto = str(valor).strip()

    if not texto:
        raise ValueError(f"{nome_campo} e obrigatorio")

    return texto


def normalizar_texto_opcional(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    return texto


def normalizar_cpf(valor: str) -> str:
    cpf = apenas_digitos(valor)

    if len(cpf) != 11:
        raise ValueError("CPF deve ter 11 digitos")

    if cpf == cpf[0] * 11:
        raise ValueError("CPF invalido")

    soma_primeiro_digito = sum(int(cpf[indice]) * (10 - indice) for indice in range(9))
    primeiro_digito = (soma_primeiro_digito * 10) % 11
    primeiro_digito = 0 if primeiro_digito == 10 else primeiro_digito

    soma_segundo_digito = sum(int(cpf[indice]) * (11 - indice) for indice in range(10))
    segundo_digito = (soma_segundo_digito * 10) % 11
    segundo_digito = 0 if segundo_digito == 10 else segundo_digito

    if primeiro_digito != int(cpf[9]) or segundo_digito != int(cpf[10]):
        raise ValueError("CPF invalido")

    return cpf


def normalizar_cep(valor: str) -> str:
    cep = apenas_digitos(valor)

    if len(cep) != 8:
        raise ValueError("CEP deve ter 8 digitos")

    return cep


def normalizar_telefone(valor: str) -> str:
    telefone = apenas_digitos(valor)

    if len(telefone) not in {10, 11}:
        raise ValueError("Telefone deve ter 10 ou 11 digitos")

    return telefone


def validar_upload_jpg(arquivo: UploadFile):
    nome_arquivo = arquivo.filename or ""

    if arquivo.content_type != "image/jpeg":
        raise HTTPException(status_code=400, detail="Envie um arquivo JPG valido")

    if not nome_arquivo.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Envie um arquivo JPG valido")

    arquivo.file.seek(0, os.SEEK_END)
    tamanho = arquivo.file.tell()
    arquivo.file.seek(0)

    if tamanho == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if tamanho > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo deve ter no maximo 8MB")

    assinatura = arquivo.file.read(3)
    arquivo.file.seek(0)

    if assinatura != b"\xff\xd8\xff":
        raise HTTPException(status_code=400, detail="Envie um arquivo JPG valido")
