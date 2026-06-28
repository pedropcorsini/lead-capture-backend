import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Lead

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


@app.on_event("startup")
def criar_tabelas():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"status": "Backend no ar"}


@app.post("/leads")
def criar_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    novo_lead = Lead(**lead.model_dump())
    db.add(novo_lead)
    db.commit()
    db.refresh(novo_lead)

    return {"id": novo_lead.id, "token": novo_lead.token}


@app.get("/leads/{token}")
def buscar_lead_por_token(token: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.token == token).first()

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

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
