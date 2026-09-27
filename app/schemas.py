from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EventoBase(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    descricao: str = Field(min_length=5, max_length=1000)
    cidade: str = Field(min_length=2, max_length=100)
    local: str = Field(min_length=2, max_length=150)
    data_evento: date
    capacidade: int = Field(gt=0, le=100000)


class EventoCreate(EventoBase):
    pass


class EventoUpdate(EventoBase):
    pass


class EventoResponse(EventoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
