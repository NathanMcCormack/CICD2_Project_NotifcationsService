from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.database import engine, get_db
from app.models import Base, DeliveryAttemptDB, NotificationDB
from app.schemas import (
    DeliveryCreate,
    DeliveryCreateForNotification,
    DeliveryRead,
    DeliveryReadWithNotification,
    DeliveryUpdate,
    NotificationCreate,
    NotificationRead,
    NotificationReadWithDeliveries,
    NotificationUpdate,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Notifications Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=error_msg)

@app.get("/health")
def health():
    return {"status": "ok", "service": "notifications"}

# -------------------- Notifications CRUD --------------------
@app.get("/api/notifications", response_model=list[NotificationRead])
def list_notifications(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(NotificationDB).order_by(NotificationDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()

@app.get("/api/notifications/{notification_id}", response_model=NotificationReadWithDeliveries)
def get_notification(notification_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(NotificationDB)
        .where(NotificationDB.id == notification_id)
        .options(selectinload(NotificationDB.deliveries))
    )
    n = db.execute(stmt).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n

@app.post("/api/notifications", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)):
    n = NotificationDB(**payload.model_dump(), status="pending")
    db.add(n)
    commit_or_rollback(db, "Notification already exists")
    db.refresh(n)
    return n

@app.patch("/api/notifications/{notification_id}", response_model=NotificationRead)
def patch_notification(notification_id: int, payload: NotificationUpdate, db: Session = Depends(get_db)):
    n = db.get(NotificationDB, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    commit_or_rollback(db, "Notification update failed")
    db.refresh(n)
    return n

@app.put("/api/notifications/{notification_id}", response_model=NotificationRead)
def put_notification(notification_id: int, payload: NotificationCreate, db: Session = Depends(get_db)):
    n = db.get(NotificationDB, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    #full update
    n.reference = payload.reference
    n.recipient = payload.recipient
    n.channel = payload.channel
    n.message = payload.message
    commit_or_rollback(db, "Notification update failed")
    db.refresh(n)
    return n

@app.delete("/api/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    n = db.get(NotificationDB, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(n)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -------------------- Delivery Attempts CRUD --------------------
@app.get("/api/deliveries", response_model=list[DeliveryRead])
def list_deliveries(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(DeliveryAttemptDB).order_by(DeliveryAttemptDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()

@app.get("/api/deliveries/{delivery_id}", response_model=DeliveryReadWithNotification)
def get_delivery(delivery_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(DeliveryAttemptDB)
        .where(DeliveryAttemptDB.id == delivery_id)
        .options(selectinload(DeliveryAttemptDB.notification))
    )
    d = db.execute(stmt).scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Delivery attempt not found")
    return d

@app.post("/api/deliveries", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
def create_delivery(payload: DeliveryCreate, db: Session = Depends(get_db)):
    n = db.get(NotificationDB, payload.notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    d = DeliveryAttemptDB(**payload.model_dump())
    db.add(d)
    commit_or_rollback(db, "Delivery attempt creation failed")
    db.refresh(d)
    return d

@app.patch("/api/deliveries/{delivery_id}", response_model=DeliveryRead)
def patch_delivery(delivery_id: int, payload: DeliveryUpdate, db: Session = Depends(get_db)):
    d = db.get(DeliveryAttemptDB, delivery_id)
    if not d:
        raise HTTPException(status_code=404, detail="Delivery attempt not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    commit_or_rollback(db, "Delivery attempt update failed")
    db.refresh(d)
    return d

@app.delete("/api/deliveries/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery(delivery_id: int, db: Session = Depends(get_db)):
    d = db.get(DeliveryAttemptDB, delivery_id)
    if not d:
        raise HTTPException(status_code=404, detail="Delivery attempt not found")
    db.delete(d)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/api/notifications/{notification_id}/deliveries", response_model=list[DeliveryRead])
def list_notification_deliveries(notification_id: int, db: Session = Depends(get_db)):
    n = db.get(NotificationDB, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    stmt = select(DeliveryAttemptDB).where(DeliveryAttemptDB.notification_id == notification_id)
    return db.execute(stmt).scalars().all()

@app.post("/api/notifications/{notification_id}/deliveries",response_model=DeliveryRead,status_code=status.HTTP_201_CREATED,)
def create_notification_delivery(notification_id: int,payload: DeliveryCreateForNotification,db: Session = Depends(get_db),):
    n = db.get(NotificationDB, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    d = DeliveryAttemptDB(notification_id=notification_id, **payload.model_dump())
    db.add(d)
    commit_or_rollback(db, "Delivery attempt creation failed")
    db.refresh(d)
    return d
