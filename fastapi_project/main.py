# main.py

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Dict
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import pandas as pd
import jwt
import datetime
from passlib.context import CryptContext
import os


SECRET_KEY = "Your_Secret_Key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# MongoDB client setup
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["dashboard_db"]
files_collection = db["files"]
users_collection = db["users"]

# Supported file types
SUPPORTED_FILE_TYPES = ["csv", "json", "xlsx", "parquet"]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Function to read and return the dataframe
async def read_file(file: UploadFile):
    if file.filename.endswith(".csv"):
        return pd.read_csv(file.file)
    elif file.filename.endswith(".json"):
        return pd.read_json(file.file)
    elif file.filename.endswith(".xlsx"):
        return pd.read_excel(file.file)
    elif file.filename.endswith(".parquet"):
        return pd.read_parquet(file.file)
    else:
        raise HTTPException(status_code=400, detail="File format not supported.")

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = await users_collection.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return user

# Models
class User(BaseModel):
    username: str
    password: str

class UserInDB(User):
    hashed_password: str

class FileData(BaseModel):
    filename: str
    data: List[Dict]

# Routes
@app.post("/signup/")
async def signup(user: User):
    user_db = await users_collection.find_one({"username": user.username})
    if user_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = {"username": user.username, "hashed_password": hashed_password}
    await users_collection.insert_one(new_user)
    return {"msg": "User created successfully"}

@app.post("/token/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if file.filename.split(".")[-1] not in SUPPORTED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    df = await read_file(file)
    data_dict = df.to_dict("records")
    result = await files_collection.insert_one({"filename": file.filename, "data": data_dict})
    return {"file_id": str(result.inserted_id), "filename": file.filename}

@app.get("/data/{file_id}", response_model=FileData)
async def get_data(file_id: str, current_user: dict = Depends(get_current_user)):
    data = await files_collection.find_one({"_id": ObjectId(file_id)})
    if not data:
        raise HTTPException(status_code=404, detail="File not found")
    return FileData(
        filename=data["filename"],
        data=data["data"]
    )
