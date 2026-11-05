"""Database access with SQLAlchemy 2.x (PostgreSQL or MySQL; SQLite only for tests)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, create_engine, func, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    attachment_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attachment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Database:
    def __init__(self, url: str):
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        self.engine = create_engine(url, **kwargs)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.sessions()

    def ping(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def count_items(self) -> int:
        with self.session() as s:
            return s.scalar(select(func.count()).select_from(Item)) or 0
