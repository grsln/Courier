from enum import Enum
from typing import Any, List

import databases
from fastapi import FastAPI
from pydantic import BaseModel
from pydantic.types import constr
from sqlalchemy import Column, MetaData, String, Table, create_engine
from sqlalchemy_utils.types.choice import ChoiceType

# DATABASE_URL = "sqlite:///./test.db"
DATABASE_URL = "postgresql://postgres:admin@127.0.0.1:5432/courier"

database = databases.Database(DATABASE_URL)

metadata = MetaData()

deliver = Table(
    "deliver",
    metadata,
    Column("id", String(5), primary_key=True, index=True, unique=True),
    Column(
        "status",
        ChoiceType([("to_do", "to_do"), ("in_progress", "in_progress"), ("done", "done")], impl=String()),
        comment="Статус доставки",
    ),
)

engine = create_engine(
    DATABASE_URL
    # , connect_args={"check_same_thread": False}
)

metadata.create_all(engine)


class StatusEnum(str, Enum):
    """Статусы доставки."""

    to_do = "to_do"
    in_progress = "in_progress"
    done = "done"


class Deliver(BaseModel):
    """Модель сериализации доставки."""

    id: constr(regex="^[a-z0-9]{2,5}$")  # type: ignore  # noqa: F722
    status: StatusEnum


class Error(BaseModel):
    """Модель сериализации ошибки."""

    error_message: str
    error: str


app = FastAPI()


@app.on_event("startup")
async def startup() -> Any:
    """Подключение к БД."""
    await database.connect()


@app.on_event("shutdown")
async def shutdown() -> Any:
    """Отключение от БД."""
    await database.disconnect()


@app.get("/deliveries/", response_model=List[Deliver])
async def get_deliveries() -> Any:
    """Получение списка доставок."""
    query = deliver.select()
    return await database.fetch_all(query)


async def get_deliver(id_deliver: str) -> Any:
    """Получение доставки с номером id_deliver."""
    query = deliver.select().where(deliver.c.id == id_deliver)
    return await database.fetch_one(query)


def next_status(current_status: StatusEnum) -> StatusEnum:
    """Функция возвращает следующий статус для current_status."""
    states = {
        StatusEnum.to_do: StatusEnum.in_progress,
        StatusEnum.in_progress: StatusEnum.done,
        StatusEnum.done: StatusEnum.to_do,
    }
    return states[current_status]


@app.post("/deliveries/", responses={200: {"model": Deliver}, 400: {"model": Error}, 500: {"model": Error}})
async def post_deliveries(del_: Deliver) -> Any:
    """Создание новой доставки или обновление статуса доставки."""
    founded_deliver = await get_deliver(id_deliver=del_.id)
    if founded_deliver:
        if next_status(founded_deliver.get("status")) == del_.status:
            query = deliver.update().where(deliver.c.id == del_.id).values(status=del_.status)
        else:
            return {"error_message": "Статус не изменен. Неверный статус.", "error": "Ошибка."}, 400
            # query = deliver.update().where(deliver.c.id == del_.id).values(status=founded_deliver.get("status"))
    else:
        query = deliver.insert().values(id=del_.id, status=del_.status)
    last_record_id = await database.execute(query)
    if not last_record_id:
        saved_deliver = await get_deliver(id_deliver=del_.id)
        if saved_deliver:
            return saved_deliver
        else:
            return {"error_message": "Ошибка сохранения.", "error": "Ошибка."}, 500
    return {**del_.dict()}
