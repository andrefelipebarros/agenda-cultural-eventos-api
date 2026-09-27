import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agenda Cultural API",
    version="1.0.0",
    description="API principal para gerenciamento de eventos culturais.",
)

INSCRICOES_API_URL = os.getenv("INSCRICOES_API_URL", "http://localhost:8001")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/eventos", response_model=schemas.EventoResponse, status_code=status.HTTP_201_CREATED)
def criar_evento(evento: schemas.EventoCreate, db: Session = Depends(get_db)):
    novo_evento = models.Evento(**evento.model_dump())
    db.add(novo_evento)
    db.commit()
    db.refresh(novo_evento)
    return novo_evento


@app.get("/eventos", response_model=list[schemas.EventoResponse])
def listar_eventos(db: Session = Depends(get_db)):
    return db.query(models.Evento).order_by(models.Evento.data_evento).all()


@app.get("/eventos/{evento_id}", response_model=schemas.EventoResponse)
def buscar_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return evento


@app.put("/eventos/{evento_id}", response_model=schemas.EventoResponse)
def atualizar_evento(
    evento_id: int,
    dados: schemas.EventoUpdate,
    db: Session = Depends(get_db),
):
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    for campo, valor in dados.model_dump().items():
        setattr(evento, campo, valor)

    db.commit()
    db.refresh(evento)
    return evento


@app.delete("/eventos/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    db.delete(evento)
    db.commit()


@app.get("/eventos/{evento_id}/clima")
async def consultar_clima(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    async with httpx.AsyncClient(timeout=10.0) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": evento.cidade,
                "count": 1,
                "language": "pt",
                "format": "json",
                "countryCode": "BR",
            },
        )

        if geo.status_code != 200:
            raise HTTPException(status_code=502, detail="Falha ao consultar a localização")

        resultados = geo.json().get("results", [])
        if not resultados:
            raise HTTPException(status_code=404, detail="Cidade não encontrada na API externa")

        localizacao = resultados[0]

        clima = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": localizacao["latitude"],
                "longitude": localizacao["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
        )

        if clima.status_code != 200:
            raise HTTPException(status_code=502, detail="Falha ao consultar o clima")

        dados_clima = clima.json()

    return {
        "evento_id": evento.id,
        "cidade": evento.cidade,
        "localizacao_encontrada": localizacao["name"],
        "estado": localizacao.get("admin1"),
        "clima_atual": dados_clima.get("current"),
        "unidades": dados_clima.get("current_units"),
        "fonte": "Open-Meteo",
    }


@app.get("/eventos/{evento_id}/inscricoes")
async def listar_inscricoes_do_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resposta = await client.get(
            f"{INSCRICOES_API_URL}/inscricoes/evento/{evento_id}"
        )

    if resposta.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar a API de inscrições",
        )

    inscricoes = resposta.json()

    return {
        "evento": {
            "id": evento.id,
            "titulo": evento.titulo,
            "capacidade": evento.capacidade,
        },
        "total_inscritos": len(inscricoes),
        "vagas_disponiveis": max(evento.capacidade - len(inscricoes), 0),
        "inscricoes": inscricoes,
    }
