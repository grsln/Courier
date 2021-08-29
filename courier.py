from enum import Enum
from typing import List

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
    Column("status",
           ChoiceType([("to_do", "to_do"), ("in_progress", "in_progress"), ("done", "done")], impl=String()),
           comment="Статус доставки"),
)

engine = create_engine(
    DATABASE_URL
    # , connect_args={"check_same_thread": False}
)

metadata.create_all(engine)


class StatusEnum(str, Enum):
    to_do = 'to_do'
    in_progress = 'in_progress'
    done = 'done'


class Deliver(BaseModel):
    id: constr(regex=r'^[a-z0-9]{2,5}$')
    status: StatusEnum


class Error(BaseModel):
    error_message: str
    error: str


# class PostDeliver(GenericModel, Generic[DataT]):
#     deliveries = Optional[Deliver]
#     error = Optional[Error]
#
#     @validator('error', always=True)
#     def check_consistency(cls, v, values):
#         if v is not None and values['deliveries'] is not None:
#             raise ValueError('must not provide both data and error')
#         if v is None and values.get('deliveries') is None:
#             raise ValueError('must provide data or error')
#         return v


app = FastAPI()


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/deliveries/", response_model=List[Deliver])
async def get_deliveries():
    query = deliver.select()
    return await database.fetch_all(query)


async def get_deliver(id_deliver):
    query = deliver.select().where(deliver.c.id == id_deliver)
    return await database.fetch_one(query)


def next_status(current_status):
    states = {StatusEnum.to_do: StatusEnum.in_progress, StatusEnum.in_progress: StatusEnum.done,
              StatusEnum.done: StatusEnum.to_do}
    return states[current_status]


@app.post("/deliveries/", response_model=Deliver)
async def post_deliveries(del_: Deliver):
    founded_deliver = await get_deliver(id_deliver=del_.id)
    if founded_deliver:
        if next_status(founded_deliver.get('status')) == del_.status:
            query = deliver.update().where(deliver.c.id == del_.id).values(status=del_.status)
        else:
            query = deliver.update().where(deliver.c.id == del_.id).values(status=founded_deliver.get('status'))
    else:
        query = deliver.insert().values(id=del_.id, status=del_.status)
    last_record_id = await database.execute(query)
    if last_record_id:
        saved_deliver = get_deliver(id_deliver=del_.id)
        return saved_deliver
    return {**del_.dict()}
