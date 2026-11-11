import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, PositiveInt
from sqlalchemy import CheckConstraint, DateTime, Numeric, String, create_engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("quantity > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int]
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(20), default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
BOOK_SERVICE_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:8000").rstrip("/")
app = FastAPI(title="Order Service", version="1.0.0")


class OrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    book_id: PositiveInt
    quantity: int = Field(strict=True, ge=1, le=100)


class OrderOutput(OrderInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    unit_price: Decimal
    total_price: Decimal
    status: str
    created_at: datetime


def fetch_book_price(book_id: int) -> Decimal:
    try:
        with httpx.Client(timeout=3.0, trust_env=False) as client:
            response = client.get(f"{BOOK_SERVICE_URL}/books/{book_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Book not found")
        response.raise_for_status()
        price = Decimal(str(response.json()["price"]))
        if not price.is_finite() or price <= 0 or price >= Decimal("10000000000"):
            raise ValueError("Invalid catalogue price")
        return price.quantize(Decimal("0.01"))
    except (httpx.HTTPError, ValueError, KeyError, TypeError, InvalidOperation):
        raise HTTPException(status_code=503, detail="Book service unavailable") from None


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503, content={"detail": "Order database unavailable"})


@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1 FROM orders LIMIT 1"))
    return {"status": "ready"}


@app.post("/orders", response_model=OrderOutput, status_code=201)
def create_order(data: OrderInput):
    price = fetch_book_price(data.book_id)
    with Session(engine) as session:
        order = Order(book_id=data.book_id, quantity=data.quantity,
                      unit_price=price, total_price=price * data.quantity)
        session.add(order)
        session.commit()
        session.refresh(order)
        return OrderOutput.model_validate(order)


@app.get("/orders/{order_id}", response_model=OrderOutput)
def get_order(order_id: PositiveInt):
    with Session(engine) as session:
        order = session.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderOutput.model_validate(order)
