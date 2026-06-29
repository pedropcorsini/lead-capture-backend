import os
import re
from io import BytesIO
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import boto3
from dotenv import load_dotenv


load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

if not S3_BUCKET_NAME:
    raise RuntimeError("S3_BUCKET_NAME nao foi configurada.")

if not S3_REGION:
    raise RuntimeError("S3_REGION nao foi configurada.")

s3_client = boto3.client(
    "s3",
    region_name=S3_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def gerar_chave_s3(cpf: str, pasta: str) -> str:
    cpf_limpo = re.sub(r"\D", "", cpf) #cpf limpo, sem . e -
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")

    return f"{pasta}/{cpf_limpo}/{timestamp}.jpg"


def montar_url_s3(chave: str) -> str:
    return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{chave}" 


def extrair_chave_s3_de_url(url_s3: str) -> str:
    url = urlparse(url_s3) 
    host = url.netloc
    caminho = unquote(url.path.lstrip("/"))

    if not caminho:
        raise ValueError("URL do S3 sem chave do arquivo")

    if host.startswith(f"{S3_BUCKET_NAME}.s3."):
        return caminho

    host_path_style = f"s3.{S3_REGION}.amazonaws.com"
    prefixo_path_style = f"{S3_BUCKET_NAME}/"

    if host == host_path_style and caminho.startswith(prefixo_path_style):
        return caminho[len(prefixo_path_style):]

    raise ValueError("URL do S3 nao pertence ao bucket configurado")


def gerar_url_temporaria_s3(url_s3: str, tempo_expiracao: int = 300) -> str:
    """
    Função que gera uma URL assinada temporária com duração de 5 minutos
    """
    chave = extrair_chave_s3_de_url(url_s3)
    nome_arquivo = chave.rsplit("/", 1)[-1] or "card.jpg"

    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": S3_BUCKET_NAME,
            "Key": chave,
            "ResponseContentDisposition": f'attachment; filename="{nome_arquivo}"',
            "ResponseContentType": "image/jpeg",
        },
        ExpiresIn=tempo_expiracao,
    )


def enviar_jpg_para_s3(arquivo, cpf: str, pasta: str) -> str:
    chave = gerar_chave_s3(cpf=cpf, pasta=pasta)

    s3_client.upload_fileobj(
        arquivo.file,
        S3_BUCKET_NAME,
        chave,
        ExtraArgs={"ContentType": "image/jpeg"},
    )

    return montar_url_s3(chave)


def baixar_arquivo_s3(url_s3: str) -> bytes:
    chave = extrair_chave_s3_de_url(url_s3)
    resposta = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=chave)

    return resposta["Body"].read()


def enviar_bytes_jpg_para_s3(conteudo: bytes, cpf: str, pasta: str) -> str:
    chave = gerar_chave_s3(cpf=cpf, pasta=pasta)

    s3_client.upload_fileobj(
        BytesIO(conteudo),
        S3_BUCKET_NAME,
        chave,
        ExtraArgs={"ContentType": "image/jpeg"},
    )

    return montar_url_s3(chave)
