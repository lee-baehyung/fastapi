from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict

app = FastAPI()


class GenderEnum(str, Enum):
    male = "male"
    female = "female"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=0, le=120)
    gender: GenderEnum


class UserModel:
    def __init__(self, id: int, username: str, age: int, gender: GenderEnum):
        self.id = id
        self.username = username
        self.age = age
        self.gender = gender


fake_db: Dict[int, UserModel] = {}
user_id_counter = 1


@app.post("/users")
def create_user(user: UserCreate):
    global user_id_counter

    new_user = UserModel(
        id=user_id_counter,
        username=user.username,
        age=user.age,
        gender=user.gender
    )
    fake_db[user_id_counter] = new_user
    user_id_counter += 1

    return {"id": new_user.id}
