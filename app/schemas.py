from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    class Config: from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


# ---------- Network ----------
class NetworkIn(BaseModel):
    name: str


class NetworkOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    class Config: from_attributes = True


# ---------- Node / Pipe ----------
NodeType = Literal["reservoir", "tank", "pump", "valve", "junction", "consumer"]
Status = Literal["ok", "warn", "alert"]
Material = Literal["PVC", "DI", "Steel", "HDPE"]


class NodeIn(BaseModel):
    ext_id: str
    type: NodeType
    label: str
    x: float
    y: float
    pressure: float = 0
    demand: Optional[float] = None
    level: Optional[float] = None
    rated_kw: Optional[float] = None
    elevation: Optional[float] = None
    leak_prob: Optional[float] = None
    status: Status = "ok"


class NodePatch(BaseModel):
    label: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    pressure: Optional[float] = None
    demand: Optional[float] = None
    level: Optional[float] = None
    rated_kw: Optional[float] = None
    elevation: Optional[float] = None
    leak_prob: Optional[float] = None
    status: Optional[Status] = None


class NodeOut(NodeIn):
    id: int
    class Config: from_attributes = True


class PipeIn(BaseModel):
    ext_id: str
    from_ext: str
    to_ext: str
    diameter: float
    flow: float = 0
    velocity: float = 0
    headloss: float = 0
    material: Material = "PVC"
    age: int = 0


class PipePatch(BaseModel):
    diameter: Optional[float] = None
    flow: Optional[float] = None
    velocity: Optional[float] = None
    headloss: Optional[float] = None
    material: Optional[Material] = None
    age: Optional[int] = None


class PipeOut(PipeIn):
    id: int
    class Config: from_attributes = True


# ---------- Telemetry ----------
class TelemetryIn(BaseModel):
    node_ext: str
    metric: str
    value: float


class TelemetryOut(TelemetryIn):
    id: int
    ts: datetime
    class Config: from_attributes = True


# ---------- Scenario ----------
ScenarioKind = Literal["pop", "pump", "burst", "res", "solar"]


class ScenarioRun(BaseModel):
    name: str
    kind: ScenarioKind
    params: dict[str, Any] = {}


class ScenarioOut(BaseModel):
    id: int
    name: str
    kind: str
    params: dict | None
    baseline_metrics: dict | None
    scenario_metrics: dict | None
    created_at: datetime
    class Config: from_attributes = True


# ---------- Energy ----------
class HourSchedule(BaseModel):
    hour: int
    tariff: float
    pump_kw: float
    duty: float


class ScheduleOut(BaseModel):
    schedule: list[HourSchedule]
    daily_kwh: float
    daily_cost: float
    baseline_cost: float
    savings: float
    co2_kg: float


# ---------- Leaks ----------
class LeakOut(BaseModel):
    node_ext: str
    prob: float
    zone: str
    severity: str


class LeaksResponse(BaseModel):
    leaks: list[LeakOut]
    updated_nodes: int


# ---------- Forecast ----------
class ForecastPoint(BaseModel):
    t: str
    actual: float | None = None
    forecast: float
    lower: float
    upper: float


class ForecastOut(BaseModel):
    horizon: str
    points: list[ForecastPoint]


# ---------- Maintenance / Quality / Carbon ----------
class AssetHealth(BaseModel):
    id: str
    type: str
    rul: int
    health: int
    cycles: int
    note: str


class WorkOrderIn(BaseModel):
    asset_id: str
    title: str
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    notes: str | None = None


class WorkOrderOut(WorkOrderIn):
    id: int
    status: str
    created_at: datetime
    class Config: from_attributes = True


class QualityIn(BaseModel):
    node_ext: str
    chlorine: float | None = None
    turbidity: float | None = None
    ph: float | None = None
    temperature: float | None = None


class QualityOut(QualityIn):
    id: int
    ts: datetime
    class Config: from_attributes = True


class CarbonOut(BaseModel):
    kwh_today: float
    kg_co2_today: float
    grid_factor: float
    trend_7d: list[float]
