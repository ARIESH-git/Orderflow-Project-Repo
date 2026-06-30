from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from db import ensure_orders_table, ensure_users_table, orders_table, users_table, dynamodb
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    build_github_authorize_url,
    verify_state,
    exchange_code_for_github_user,
)
from prometheus_fastapi_instrumentator import Instrumentator
class AuthRequest(BaseModel):
    username: str
    password: str
@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_orders_table()
    ensure_users_table()
    yield
app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)
producer = KafkaProducer(
    bootstrap_servers="kafka:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)
@app.get("/health")
def health_check():
    return {"status": "ok"}
@app.post("/auth/register")
def register(payload: AuthRequest):
    try:
        users_table.put_item(
            Item={
                "username": payload.username,
                "password_hash": hash_password(payload.password),
                "auth_provider": "local",
            },
            ConditionExpression="attribute_not_exists(username)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"username": payload.username, "status": "registered"}
@app.post("/auth/login")
def login(payload: AuthRequest):
    result = users_table.get_item(Key={"username": payload.username})
    user = result.get("Item")
    if not user or user.get("auth_provider") != "local":
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(payload.username)
    return {"access_token": token, "token_type": "bearer"}
@app.get("/auth/github/login")
def github_login():
    return RedirectResponse(build_github_authorize_url())
@app.get("/auth/github/callback")
def github_callback(code: str, state: str):
    if not verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    github_user = exchange_code_for_github_user(code)
    username = github_user["login"]
    try:
        users_table.put_item(
            Item={"username": username, "auth_provider": "github"},
            ConditionExpression="attribute_not_exists(username)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        pass  # already linked from a previous login, just sign them in again
    token = create_access_token(username)
    return {"access_token": token, "token_type": "bearer"}
@app.post("/orders")
def create_order(item: str, quantity: int, current_user: str = Depends(get_current_user)):
    import random
    if random.random() < 0.5:
        raise HTTPException(status_code=500, detail="Simulated bad deploy failure")
    with open("/tmp/debug.log", "a") as f:
        f.write("ORDER ROUTE HIT\n")
    order_id = str(uuid.uuid4())
    orders_table.put_item(Item={
        "order_id": order_id,
        "item": item,
        "quantity": quantity,
        "placed_by": current_user,
        "status": "PLACED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    event = {"order_id": order_id, "item": item, "quantity": quantity}
    future = producer.send("order-placed", key=order_id.encode("utf-8"), value=event)
    try:
        m = future.get(timeout=10)
        with open("/tmp/debug.log", "a") as f:
            f.write(f"OK offset={m.offset}\n")
    except Exception as e:
        with open("/tmp/debug.log", "a") as f:
            f.write(f"FAILED: {e}\n")
        raise
    return {"order_id": order_id, "status": "order placed"}
