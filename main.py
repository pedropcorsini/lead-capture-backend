import os
import secrets
from typing import Optional

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, ValidationInfo, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from card_generator import gerar_card_jpg
from database import Base, engine, get_db
from models import Lead
from qr_code import gerar_qrcode_png
from storage import (
    baixar_arquivo_s3,
    enviar_bytes_jpg_para_s3,
    enviar_jpg_para_s3,
    gerar_url_temporaria_s3,
)
from validations import (
    apenas_digitos,
    normalizar_cep,
    normalizar_cpf,
    normalizar_telefone,
    normalizar_texto_obrigatorio,
    normalizar_texto_opcional,
    validar_upload_jpg,
)

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

MOLDURAS = [
    {"id": "azul", "nome": "Azul", "arquivo": "moldura-azul.png"},
    {"id": "branca", "nome": "Branca", "arquivo": "moldura-branca.png"},
    {"id": "festiva", "nome": "Festiva", "arquivo": "moldura-festiva.png"},
    {"id": "gold", "nome": "Gold", "arquivo": "moldura-gold.png"},
]

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
    email: EmailStr
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

    @field_validator("nome", "cidade", mode="before")
    @classmethod
    def validar_textos_obrigatorios(cls, valor, info: ValidationInfo):
        return normalizar_texto_obrigatorio(valor, info.field_name)

    @field_validator("email", mode="before")
    @classmethod
    def validar_email_obrigatorio(cls, valor):
        return normalizar_texto_obrigatorio(valor, "email")

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, valor: EmailStr):
        return str(valor).lower()

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf(cls, valor):
        return normalizar_cpf(valor)

    @field_validator("telefone", mode="before")
    @classmethod
    def validar_telefone(cls, valor):
        return normalizar_telefone(valor)

    @field_validator("cep", mode="before")
    @classmethod
    def validar_cep(cls, valor):
        return normalizar_cep(valor)

    @field_validator(
        "data_nascimento",
        "genero",
        "instagram",
        "empresa",
        "cargo",
        "setor",
        "linkedin",
        "site",
        "observacoes",
        mode="before",
    )
    @classmethod
    def normalizar_textos_opcionais(cls, valor):
        return normalizar_texto_opcional(valor)


def buscar_lead_ou_404(token: str, db: Session):
    lead = db.query(Lead).filter(Lead.token == token).first()

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    return lead


def garantir_card_gerado(lead: Lead):
    if not lead.url_card:
        raise HTTPException(status_code=404, detail="Card ainda nao foi gerado")


def garantir_foto_enviada(lead: Lead):
    if not lead.url_foto:
        raise HTTPException(status_code=404, detail="Foto com moldura ainda nao foi enviada")


def montar_url_download_card(request: Request, token: str) -> str:
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

    if public_base_url:
        return f"{public_base_url}/leads/{token}/download-card"

    return str(request.url_for("baixar_card_lead", token=token))


def montar_base_url(request: Request) -> str:
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

    if public_base_url:
        return public_base_url

    return str(request.base_url).rstrip("/")


def verificar_admin(x_admin_api_key: Optional[str] = Header(default=None)):
    admin_api_key = os.getenv("ADMIN_API_KEY")

    if not admin_api_key:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY nao configurada")

    if not x_admin_api_key or not secrets.compare_digest(x_admin_api_key, admin_api_key):
        raise HTTPException(status_code=401, detail="Nao autorizado")


def buscar_lead_por_id_ou_404(lead_id: int, db: Session):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    return lead


def lead_para_admin(lead: Lead):
    return {
        "id": lead.id,
        "nome": lead.nome,
        "cpf": lead.cpf,
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


def redirecionar_para_card_temporario(lead: Lead):
    try:
        url_temporaria = gerar_url_temporaria_s3(lead.url_card)
    except (BotoCoreError, ClientError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Erro ao gerar URL temporaria do card") from exc

    return RedirectResponse(url=url_temporaria)


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


@app.get("/molduras")
def listar_molduras(request: Request):
    base_url = montar_base_url(request)

    return [
        {
            "id": moldura["id"],
            "nome": moldura["nome"],
            "url": f"{base_url}/assets/molduras/{moldura['arquivo']}",
        }
        for moldura in MOLDURAS
    ]


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
    validar_upload_jpg(arquivo)

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
    validar_upload_jpg(arquivo)

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


@app.post("/leads/{token}/gerar-card")
def gerar_card_lead(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    lead = buscar_lead_ou_404(token=token, db=db)
    garantir_foto_enviada(lead)

    url_download = montar_url_download_card(request=request, token=token)

    try:
        foto_bytes = baixar_arquivo_s3(lead.url_foto)
        card_bytes = gerar_card_jpg(lead=lead, foto_bytes=foto_bytes, url_download=url_download)
        lead.url_card = enviar_bytes_jpg_para_s3(
            conteudo=card_bytes,
            cpf=lead.cpf,
            pasta="candidatos/cards",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail="Erro ao gerar card") from exc

    db.commit()
    db.refresh(lead)

    return {"id": lead.id, "token": lead.token, "url_card": lead.url_card}


@app.get("/leads/{token}/download-card", name="baixar_card_lead") 
def baixar_card_lead(token: str, db: Session = Depends(get_db)): 
    lead = buscar_lead_ou_404(token=token, db=db) #busca o token no banco
    garantir_card_gerado(lead) #verifica se o url_card já existe

    return redirecionar_para_card_temporario(lead) #redireciona para uma URL temporária assinada do S3


@app.get("/leads/{token}/qrcode")
def gerar_qrcode_download_card(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
): 
    lead = buscar_lead_ou_404(token=token, db=db) #busca o lead no banco
    garantir_card_gerado(lead) #verifica se o card ja foi gerado

    url_download = montar_url_download_card(request=request, token=token) #monta a url de download
    qrcode_png = gerar_qrcode_png(url_download) #gera um qrcode, apontando para /leads/{token}/download-card

    return StreamingResponse(qrcode_png, media_type="image/png")


@app.get("/admin/leads")
def listar_leads_admin(
    nome: Optional[str] = Query(default=None),
    cpf: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_autenticado: None = Depends(verificar_admin),
):
    query = db.query(Lead)

    if nome and nome.strip():
        query = query.filter(Lead.nome.ilike(f"%{nome.strip()}%"))

    if cpf and cpf.strip():
        cpf_limpo = apenas_digitos(cpf)

        if len(cpf_limpo) != 11:
            raise HTTPException(status_code=400, detail="CPF deve ter 11 digitos")

        query = query.filter(Lead.cpf == cpf_limpo)

    total = query.count()
    leads = query.order_by(Lead.criado_em.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [lead_para_admin(lead) for lead in leads],
    }


@app.get("/admin/leads/{lead_id}")
def detalhar_lead_admin(
    lead_id: int,
    db: Session = Depends(get_db),
    admin_autenticado: None = Depends(verificar_admin),
):
    lead = buscar_lead_por_id_ou_404(lead_id=lead_id, db=db)

    return lead_para_admin(lead)


@app.get("/admin/leads/{lead_id}/download-card")
def baixar_card_admin(
    lead_id: int,
    db: Session = Depends(get_db),
    admin_autenticado: None = Depends(verificar_admin),
):
    lead = buscar_lead_por_id_ou_404(lead_id=lead_id, db=db)
    garantir_card_gerado(lead)

    return redirecionar_para_card_temporario(lead)
