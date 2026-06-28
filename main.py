import os
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Lead
from storage import enviar_jpg_para_s3

app = FastAPI()

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class LeadCreate(BaseModel): #valida os campos
    nome: str
    cpf: str
    email: str
    telefone: str
    cep: str
    cidade: str
    data_nascimento: Optional[str] = None
    genero: Optional[str] = None
    instagram: Optional[str] = None
    empresa: Optional[str] = None
    cargo: Optional[str] = None
    setor: Optional[str] = None
    linkedin: Optional[str] = None
    site: Optional[str] = None
    observacoes: Optional[str] = None


def buscar_lead_ou_404(token: str, db: Session):
    lead = db.query(Lead).filter(Lead.token == token).first()

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    return lead


def validar_arquivo_jpg(arquivo: UploadFile):
    if arquivo.content_type not in {"image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=400, detail="Envie um arquivo JPG")


@app.on_event("startup")
def criar_tabelas():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"status": "Backend no ar"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@app.post("/leads")
def criar_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    novo_lead = Lead(**lead.model_dump())
    db.add(novo_lead)
    db.commit()
    db.refresh(novo_lead)

    return {"id": novo_lead.id, "token": novo_lead.token}


@app.get("/leads/{token}")
def buscar_lead_por_token(token: str, db: Session = Depends(get_db)):
    lead = buscar_lead_ou_404(token=token, db=db)

    return {
        "id": lead.id,
        "nome": lead.nome,
        "email": lead.email,
        "telefone": lead.telefone,
        "cep": lead.cep,
        "cidade": lead.cidade,
        "data_nascimento": lead.data_nascimento,
        "genero": lead.genero,
        "instagram": lead.instagram,
        "empresa": lead.empresa,
        "cargo": lead.cargo,
        "setor": lead.setor,
        "linkedin": lead.linkedin,
        "site": lead.site,
        "observacoes": lead.observacoes,
        "url_foto": lead.url_foto,
        "url_card": lead.url_card,
        "token": lead.token,
        "criado_em": lead.criado_em,
    }


@app.post("/leads/{token}/foto")
def enviar_foto_lead(
    token: str,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    lead = buscar_lead_ou_404(token=token, db=db)
    validar_arquivo_jpg(arquivo)

    try:
        lead.url_foto = enviar_jpg_para_s3(
            arquivo=arquivo,
            cpf=lead.cpf,
            pasta="candidatos/fotos-moldura",
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail="Erro ao enviar foto para o S3") from exc

    db.commit()
    db.refresh(lead)

    return {"id": lead.id, "token": lead.token, "url_foto": lead.url_foto}


@app.post("/leads/{token}/card")
def enviar_card_lead(
    token: str,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    lead = buscar_lead_ou_404(token=token, db=db)
    validar_arquivo_jpg(arquivo)

    try:
        lead.url_card = enviar_jpg_para_s3(
            arquivo=arquivo,
            cpf=lead.cpf,
            pasta="candidatos/cards",
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail="Erro ao enviar card para o S3") from exc

    db.commit()
    db.refresh(lead)

    return {"id": lead.id, "token": lead.token, "url_card": lead.url_card}
