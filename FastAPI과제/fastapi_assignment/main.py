from fastapi import FastAPI, HTTPException, Path, Query, Depends
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy import Column, Integer, String, Enum as SqlEnum, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session


DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class GenderEnum(str, Enum):
    male = "male"
    female = "female"


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., ge=0, le=120)
    gender: GenderEnum


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=50)
    age: int | None = Field(None, ge=0, le=120)


class UserQueryParams(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., gt=0, description="0보다 큰 값만 허용")
    gender: GenderEnum


class UserResponse(BaseModel):
    id: int
    username: str
    age: int
    gender: GenderEnum


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(SqlEnum(GenderEnum), nullable=False)

    @classmethod
    def create(cls, db: Session, **kwargs):
        user = cls(**kwargs)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def all(cls, db: Session):
        return db.query(cls).all()

    def delete(self, db: Session):
        db.delete(self)
        db.commit()


Base.metadata.create_all(bind=engine)


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users", response_model=dict)
async def create_user(data: UserCreateRequest, db: Session = Depends(get_db)):
    user = UserModel.create(db, **data.model_dump())
    return {"id": user.id}


@app.get("/users", response_model=list[UserResponse])
async def get_all_users(db: Session = Depends(get_db)):
    users = UserModel.all(db)
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    return [UserResponse.model_validate(u) for u in users]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., ge=1, description="조회할 유저의 ID (양수)"),
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int = Path(..., ge=1, description="업데이트할 유저의 ID (양수)"),
    data: UserUpdateRequest = None,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.username is not None:
        user.username = data.username
    if data.age is not None:
        user.age = data.age

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int = Path(..., ge=1, description="삭제할 유저의 ID (양수)"),
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.delete(db)
    return {"detail": f"User: {user_id}, Successfully Deleted."}


@app.get("/users/search", response_model=list[UserResponse])
async def search_users(
    username: str = Query(..., min_length=1, max_length=50),
    age: int = Query(..., gt=0),
    gender: GenderEnum = Query(...),
    db: Session = Depends(get_db)
):
    # Pydantic 검증
    params = UserQueryParams(username=username, age=age, gender=gender)

    users = db.query(UserModel).filter_by(
        username=params.username,
        age=params.age,
        gender=params.gender
    ).all()

    if not users:
        raise HTTPException(status_code=404, detail="No matching users found")

    return [UserResponse.model_validate(u) for u in users]
