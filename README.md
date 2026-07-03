# Lead Capture Backend

API do sistema de captação de leads com foto para eventos. Recebe cadastros, armazena fotos e cards no S3, gera QR codes e expõe um painel administrativo protegido por chave.

Frontend: [lead-capture-frontend](https://github.com/pedropcorsini/lead-capture-frontend)
API em produção: https://lead-capture-backend-production.up.railway.app

## Stack

- **Python 3** + **FastAPI**
- **SQLAlchemy** (ORM)
- **PostgreSQL** (Railway)
- **AWS S3** (armazenamento de fotos e cards)
- **Pillow** (geração da imagem final do card)
- **qrcode** (geração do QR code)

## Fluxo

```
POST /leads                    -> cria o lead, retorna um token
POST /leads/{token}/foto       -> recebe a foto (já composta com a moldura)
POST /leads/{token}/gerar-card -> monta o card final (foto + dados + QR) e salva no S3
GET  /leads/{token}/qrcode     -> gera o QR code que aponta para o download
GET  /leads/{token}/download-card -> redireciona para uma URL assinada temporária do S3
```

Painel admin (autenticado via header `X-Admin-Api-Key`):

```
GET /admin/leads                       -> lista/busca leads (por nome ou CPF, paginado)
GET /admin/leads/{lead_id}             -> detalhe de um lead
GET /admin/leads/{lead_id}/download-card -> baixa o card de um lead específico
```

## Rodando localmente

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Crie um `.env` na raiz (veja `.env.example`) com:

```env
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
CORS_ORIGINS=http://localhost:3000
S3_BUCKET_NAME=nome-do-bucket
S3_REGION=sa-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
PUBLIC_BASE_URL=http://localhost:8000
ADMIN_API_KEY=defina-uma-chave-forte
CARD_EVENT_TITLE=Nome do Evento
```

```bash
uvicorn main:app --reload
```

A API sobe em `http://localhost:8000`. As tabelas são criadas automaticamente no primeiro start (`Base.metadata.create_all`).

## Estrutura

```
main.py            # rotas da API
models.py           # modelo Lead (SQLAlchemy)
database.py          # conexão com o banco
storage.py           # upload/download/URL assinada no S3
validations.py         # validação de CPF, telefone, CEP, etc
card_generator.py       # geração da imagem final do card (Pillow)
qr_code.py           # geração do QR code
assets/molduras/       # PNGs das 4 molduras disponíveis
assets/fonts/         # fonte embutida usada no card (evita depender de fonte do SO)
```

## Deploy

Railway, com deploy automático a partir da branch `main`.
