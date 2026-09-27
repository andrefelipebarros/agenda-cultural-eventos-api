from sqlalchemy import Column, Date, Integer, String, Text

from .database import Base


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=False)
    cidade = Column(String(100), nullable=False)
    local = Column(String(150), nullable=False)
    data_evento = Column(Date, nullable=False)
    capacidade = Column(Integer, nullable=False)
