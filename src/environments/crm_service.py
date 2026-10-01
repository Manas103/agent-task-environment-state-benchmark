"""The CRM work environment: accounts, contacts, opportunities. A real FastAPI
process bound to its own port and its own Postgres schema (crm). Run standalone with:
    uvicorn src.environments.crm_service:app --host 127.0.0.1 --port 8801
"""

from fastapi import FastAPI
from pydantic import BaseModel

from src import db

app = FastAPI(title="crm-environment")


@app.on_event("startup")
def _startup():
    db.init_schema("crm")


def _conn():
    return db.get_conn("crm")


class CreateAccount(BaseModel):
    id: str
    name: str
    tier: str
    industry: str


class UpdateAccountTier(BaseModel):
    id: str
    tier: str


class CreateContact(BaseModel):
    id: str
    account_id: str
    name: str
    email: str


class DeleteContact(BaseModel):
    id: str


class CreateOpportunity(BaseModel):
    id: str
    account_id: str
    stage: str
    amount: float


@app.post("/accounts")
def create_account(body: CreateAccount):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (id, name, tier, industry) VALUES (%s,%s,%s,%s)",
            (body.id, body.name, body.tier, body.industry),
        )
    conn.close()
    return {"ok": True, "id": body.id}


@app.post("/accounts/tier")
def update_account_tier(body: UpdateAccountTier):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE accounts SET tier=%s WHERE id=%s", (body.tier, body.id))
        affected = cur.rowcount
    conn.close()
    return {"ok": affected == 1, "id": body.id}


@app.post("/contacts")
def create_contact(body: CreateContact):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO contacts (id, account_id, name, email) VALUES (%s,%s,%s,%s)",
            (body.id, body.account_id, body.name, body.email),
        )
    conn.close()
    return {"ok": True, "id": body.id}


@app.post("/contacts/delete")
def delete_contact(body: DeleteContact):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE contacts SET deleted=TRUE WHERE id=%s", (body.id,))
        affected = cur.rowcount
    conn.close()
    return {"ok": affected == 1, "id": body.id}


@app.post("/opportunities")
def create_opportunity(body: CreateOpportunity):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO opportunities (id, account_id, stage, amount) VALUES (%s,%s,%s,%s)",
            (body.id, body.account_id, body.stage, body.amount),
        )
    conn.close()
    return {"ok": True, "id": body.id}


@app.get("/health")
def health():
    return {"ok": True, "environment": "crm"}
