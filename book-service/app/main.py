import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, PositiveInt
from sqlalchemy import CheckConstraint, Numeric, String, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (CheckConstraint("price > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(200))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))


engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
app = FastAPI(title="Book Service", version="1.0.0")


class BookInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BookOutput(BookInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503, content={"detail": "Book database unavailable"})


@app.get("/health")
def health():
    return {"status": "ok", "service": "book-service"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1 FROM books LIMIT 1"))
    return {"status": "ready"}


@app.post("/books", response_model=BookOutput, status_code=201)
def create_book(data: BookInput):
    with Session(engine) as session:
        book = Book(**data.model_dump())
        session.add(book)
        session.commit()
        session.refresh(book)
        return BookOutput.model_validate(book)


@app.get("/books", response_model=list[BookOutput])
def list_books():
    with Session(engine) as session:
        return [BookOutput.model_validate(b) for b in session.scalars(select(Book).order_by(Book.id))]


@app.get("/books/{book_id}", response_model=BookOutput)
def get_book(book_id: PositiveInt):
    with Session(engine) as session:
        book = session.get(Book, book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookOutput.model_validate(book)
