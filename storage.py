import os
import re
from datetime import datetime, timezone

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
    cpf_limpo = re.sub(r"\D", "", cpf)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")

    return f"{pasta}/{cpf_limpo}/{timestamp}.jpg"


def montar_url_s3(chave: str) -> str:
    return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{chave}"


def enviar_jpg_para_s3(arquivo, cpf: str, pasta: str) -> str:
    chave = gerar_chave_s3(cpf=cpf, pasta=pasta)

    s3_client.upload_fileobj(
        arquivo.file,
        S3_BUCKET_NAME,
        chave,
        ExtraArgs={"ContentType": "image/jpeg"},
    )

    return montar_url_s3(chave)
