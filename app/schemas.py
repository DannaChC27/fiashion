from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100,
                        description="Product name", examples=["Oversize denim jacket"])
    descripcion: str = Field("", max_length=300,
                             description="Short description", examples=["Blue denim jacket, unisex fit"])
    precio: float = Field(..., gt=0, description="Price in COP", examples=[129900])
    talla: str = Field("M", description="Size (XS, S, M, L, XL)", examples=["M"])
    genero: str = Field("unisex", description="Target gender", examples=["mujer"])
    categoria: str = Field("general", description="Category", examples=["chaquetas"])
    estilo: str = Field("casual", description="Style", examples=["urbano"])
    disponible: bool = Field(True, description="Is it for sale?", examples=[True])
    color: str = Field("gris", max_length=30, description="Main color", examples=["azul"])
    stock: int = Field(1, ge=0, le=10000, description="Units in the store", examples=[3])


class ProductoCreate(ProductoBase):
    pass


class ProductoOut(ProductoBase):
    model_config = ConfigDict(from_attributes=True)
    id_producto: int = Field(..., examples=[1])
    libres: int = Field(0, description="Units not reserved yet (stock - open reservations)",
                        examples=[2])
    imagen: Optional[str] = Field(None, description="Real photo uploaded for the product")
    modelo_3d: Optional[str] = Field(None, description="Real 3D scan (.glb) uploaded for the product")


class ErrorOut(BaseModel):
    status: int = Field(..., examples=[404])
    message: str = Field(..., examples=["Product not found"])
    timestamp: str = Field(..., examples=["2026-10-14T22:55:56+00:00"])


class ValidationErrorOut(BaseModel):
    status: int = Field(..., examples=[422])
    message: str = Field(..., examples=["Invalid data"])
    timestamp: str = Field(..., examples=["2026-10-14T22:55:56+00:00"])
    details: list[dict] = Field(..., examples=[[{"field": "body.precio",
                                                  "problem": "Input should be greater than 0"}]])


class RecommendRequest(BaseModel):
    talla: str = Field(..., description="Customer size", examples=["M"])
    genero: str = Field(..., description="Gender / age group", examples=["mujer"])
    categoria: str = Field(..., description="Wanted category", examples=["chaquetas"])
    estilo: Optional[str] = Field(None, description="Wanted style", examples=["urbano"])
    technique: Literal["zero_shot", "few_shot", "cot"] = Field(
        "zero_shot", description="Prompting technique to use")


class RecommendResponse(BaseModel):
    technique: str
    recommendation: str
    products_considered: int
    product_ids: list[int] = Field([], description="Ids of the recommended products found in the answer")
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: int


# ---------- Probadores, reservas y notificaciones ----------

class ProbadorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30, examples=["Probador 5"])


class ProbadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_probador: int
    nombre: str
    estado: str
    cliente: str = ""
    prendas: list[str] = []


class ReservaCreate(BaseModel):
    id_producto: int = Field(..., gt=0, examples=[1])
    nombre_cliente: str = Field(..., min_length=2, max_length=80, examples=["Laura Gomez"])

    @field_validator("nombre_cliente")
    @classmethod
    def sin_espacios(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must have at least 2 letters")
        return v


class ReservaOut(BaseModel):
    id_reserva: int
    id_producto: int
    prenda: str
    talla: str
    nombre_cliente: str
    probador: str
    estado: str
    creada_en: datetime


class NotificacionOut(BaseModel):
    id_notificacion: int
    id_reserva: int
    mensaje: str
    leida: bool
    fecha: datetime
    estado_reserva: str


# ---------- Inventario ----------

class MovimientoCreate(BaseModel):
    id_producto: int = Field(..., gt=0, examples=[1])
    tipo: Literal["entrada", "salida", "ajuste"] = Field(..., examples=["entrada"])
    cantidad: int = Field(..., ge=0, le=10000, examples=[5])
    motivo: str = Field("", max_length=200, examples=["Llego pedido del proveedor"])


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_movimiento: int
    id_producto: int
    tipo: str
    cantidad: int
    motivo: str
    fecha: datetime
