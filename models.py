from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, Text

from database import Base


class Lead(Base):
    """Representa a tabela de leads capturados pelo sistema."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(Text, nullable=False)
    cpf = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    telefone = Column(Text, nullable=False)
    cep = Column(Text, nullable=False)
    cidade = Column(Text, nullable=False)
    data_nascimento = Column(Text, nullable=True)
    genero = Column(Text, nullable=True)
    instagram = Column(Text, nullable=True)
    empresa = Column(Text, nullable=True)
    cargo = Column(Text, nullable=True)
    setor = Column(Text, nullable=True)
    linkedin = Column(Text, nullable=True)
    site = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    url_foto = Column(Text, nullable=True)
    url_card = Column(Text, nullable=True)
    token = Column(Text, nullable=False, default=lambda: str(uuid4()))
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
