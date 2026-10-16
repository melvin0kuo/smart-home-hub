from sqlalchemy import JSON, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SensorMeasurement(Base):
    __tablename__ = "sensor_measurements"
    mode: Mapped[str] = mapped_column(String, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    metric: Mapped[str] = mapped_column(String, primary_key=True)
    occurred_at: Mapped[float] = mapped_column(Float, primary_key=True, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)


class SensorCursor(Base):
    __tablename__ = "sensor_history_cursors"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    synced_until: Mapped[float] = mapped_column(Float)


class SessionRecord(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    csrf: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    expires: Mapped[float] = mapped_column(Float)


class DeviceRecord(Base):
    __tablename__ = "devices"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class EntityMapping(Base):
    __tablename__ = "entity_mappings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String)
    verified: Mapped[int] = mapped_column(Integer, default=0)


class ImportedDevice(Base):
    __tablename__ = "imported_devices"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class OperationLog(Base):
    __tablename__ = "operations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String, unique=True)
    mode: Mapped[str] = mapped_column(String, index=True)
    occurred_at: Mapped[str] = mapped_column(String)
    device_id: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    code: Mapped[str | None] = mapped_column(String, nullable=True)
