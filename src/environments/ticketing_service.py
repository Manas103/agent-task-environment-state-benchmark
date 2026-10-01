"""The support-ticketing work environment: tickets only. A real FastAPI process
bound to its own port and its own Postgres schema (ticketing). Run standalone with:
    uvicorn src.environments.ticketing_service:app --host 127.0.0.1 --port 8802
"""

from fastapi import FastAPI
from pydantic import BaseModel

from src import db

app = FastAPI(title="ticketing-environment")

PRIORITY_LADDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@app.on_event("startup")
def _startup():
    db.init_schema("ticketing")


def _conn():
    return db.get_conn("ticketing")


class CreateTicket(BaseModel):
    id: str
    subject: str
    priority: str


class AssignTicket(BaseModel):
    id: str
    assignee: str


class EscalateTicket(BaseModel):
    id: str


class CloseTicket(BaseModel):
    id: str
    close_reason: str


@app.post("/tickets")
def create_ticket(body: CreateTicket):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tickets (id, subject, status, priority) VALUES (%s,%s,'OPEN',%s)",
            (body.id, body.subject, body.priority),
        )
    conn.close()
    return {"ok": True, "id": body.id}


@app.post("/tickets/assign")
def assign_ticket(body: AssignTicket):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE tickets SET assignee=%s, status='ASSIGNED' WHERE id=%s",
            (body.assignee, body.id),
        )
        affected = cur.rowcount
    conn.close()
    return {"ok": affected == 1, "id": body.id}


@app.post("/tickets/escalate")
def escalate_ticket(body: EscalateTicket):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("SELECT priority FROM tickets WHERE id=%s", (body.id,))
        row = cur.fetchone()
        if row is None:
            conn.close()
            return {"ok": False, "id": body.id}
        current = row[0]
        idx = PRIORITY_LADDER.index(current) if current in PRIORITY_LADDER else 0
        new_priority = PRIORITY_LADDER[min(idx + 1, len(PRIORITY_LADDER) - 1)]
        cur.execute("UPDATE tickets SET priority=%s WHERE id=%s", (new_priority, body.id))
    conn.close()
    return {"ok": True, "id": body.id, "priority": new_priority}


@app.post("/tickets/close")
def close_ticket(body: CloseTicket):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE tickets SET status='CLOSED', close_reason=%s WHERE id=%s",
            (body.close_reason, body.id),
        )
        affected = cur.rowcount
    conn.close()
    return {"ok": affected == 1, "id": body.id}


@app.get("/health")
def health():
    return {"ok": True, "environment": "ticketing"}
