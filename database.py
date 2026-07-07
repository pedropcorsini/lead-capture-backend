import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv() #carrega as variaveis do .env

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL nao foi configurada.")

engine = create_engine(DATABASE_URL) #conexão principal do sqlalchemy com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #cria sessoes para conversar com o banco
Base = declarative_base() #base usada pelos models


def get_db():
    """Abre uma sessão de banco por requisição e fecha ao final do uso."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
