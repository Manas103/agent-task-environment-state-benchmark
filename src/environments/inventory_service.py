"""The inventory/catalog work environment: products and per-warehouse stock. A real
FastAPI process bound to its own port and its own Postgres schema (inventory). Run
standalone with:
    uvicorn src.environments.inventory_service:app --host 127.0.0.1 --port 8803
"""

from fastapi import FastAPI
from pydantic import BaseModel

from src import db

app = FastAPI(title="inventory-environment")


@app.on_event("startup")
def _startup():
    db.init_schema("inventory")


def _conn():
    return db.get_conn("inventory")


class CreateProduct(BaseModel):
    id: str
    name: str
    category: str


class AdjustStock(BaseModel):
    product_id: str
    warehouse: str
    delta: int


class TransferStock(BaseModel):
    product_id: str
    from_warehouse: str
    to_warehouse: str
    quantity: int


class RetireProduct(BaseModel):
    id: str


def _upsert_stock(cur, product_id, warehouse, delta):
    cur.execute(
        """
        INSERT INTO stock (product_id, warehouse, quantity) VALUES (%s,%s,%s)
        ON CONFLICT (product_id, warehouse)
        DO UPDATE SET quantity = stock.quantity + EXCLUDED.quantity
        """,
        (product_id, warehouse, delta),
    )


@app.post("/products")
def create_product(body: CreateProduct):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO products (id, name, category) VALUES (%s,%s,%s)",
            (body.id, body.name, body.category),
        )
    conn.close()
    return {"ok": True, "id": body.id}


@app.post("/stock/adjust")
def adjust_stock(body: AdjustStock):
    conn = _conn()
    with conn.cursor() as cur:
        _upsert_stock(cur, body.product_id, body.warehouse, body.delta)
    conn.close()
    return {"ok": True, "id": body.product_id}


@app.post("/stock/transfer")
def transfer_stock(body: TransferStock):
    conn = _conn()
    with conn.cursor() as cur:
        _upsert_stock(cur, body.product_id, body.from_warehouse, -body.quantity)
        _upsert_stock(cur, body.product_id, body.to_warehouse, body.quantity)
    conn.close()
    return {"ok": True, "id": body.product_id}


@app.post("/products/retire")
def retire_product(body: RetireProduct):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE products SET active=FALSE WHERE id=%s", (body.id,))
        affected = cur.rowcount
    conn.close()
    return {"ok": affected == 1, "id": body.id}


@app.get("/health")
def health():
    return {"ok": True, "environment": "inventory"}
