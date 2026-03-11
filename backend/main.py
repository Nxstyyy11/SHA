"""FastAPI backend for Smart Healthcare Analytics."""

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import ml_model
from database import AuthSession, Patient, Prediction, User, append_patient_to_csv, get_db, init_db
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from ml_model import get_feature_importance, get_model_accuracy, get_model_comparison


app = FastAPI(
    title="Smart Healthcare Analytics API",
    description="API for diabetes analytics and personalized prediction history",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
IS_VERCEL = bool(os.getenv("VERCEL"))
PREDICTION_LOG_PATH = (
    os.path.join("/tmp", "smart_healthcare_analytics_predictions.log")
    if IS_VERCEL
    else os.path.join(BASE_DIR, "..", "data", ".gitkeep")
)
SESSION_TTL_DAYS = 30

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup():
    init_db()
    ml_model.load_model()  # loads RF model + populates metrics cache (feature importance, accuracy, comparison)


@app.get("/", include_in_schema=False)
def read_root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Smart Healthcare Analytics API",
        "docs": "/docs",
        "debug_cwd": os.getcwd(),
        "debug_index_path": index_path,
        "debug_exists": os.path.exists(index_path),
        "debug_isdir": os.path.isdir(FRONTEND_DIR)
    }


class PatientOut(BaseModel):
    id: int
    pregnancies: int
    glucose: float
    blood_pressure: float
    skin_thickness: float
    insulin: float
    bmi: float
    dpf: float
    age: int
    outcome: int

    class Config:
        from_attributes = True


class PredictInput(BaseModel):
    pregnancies: float = 0
    glucose: float = 120
    blood_pressure: float = 70
    skin_thickness: float = 20
    insulin: float = 80
    bmi: float = 28.0
    dpf: float = 0.5
    age: float = 30


class PredictionOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    pregnancies: float
    glucose: float
    blood_pressure: float
    skin_thickness: float
    insulin: float
    bmi: float
    dpf: float
    age: float
    prediction: int
    probability: float
    risk_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuthInput(BaseModel):
    username: str
    password: str


class AuthOut(BaseModel):
    token: str
    username: str


def serialize_prediction(pred: Prediction) -> dict:
    return PredictionOut.model_validate(pred).model_dump()


def parse_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization token required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    token = parse_bearer_token(authorization)
    session = db.query(AuthSession).filter(AuthSession.token == token).first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Strip timezone info from DB value if present (SQLAlchemy 2.x / Python 3.12+ may return aware datetimes)
    expires_at = session.expires_at.replace(tzinfo=None) if session.expires_at.tzinfo else session.expires_at
    if expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    raw = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 150000)
    return f"{salt}${raw.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, saved = stored_hash.split("$", 1)
    except ValueError:
        return False
    raw = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 150000)
    return secrets.compare_digest(raw.hex(), saved)


def create_session_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    db.add(
        AuthSession(
            user_id=user_id,
            token=token,
            created_at=now,
            expires_at=now + timedelta(days=SESSION_TTL_DAYS),
        )
    )
    db.commit()
    return token


def append_prediction_log(submitted_data: dict, output_data: dict, prediction_id: int, username: str):
    log_row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "prediction_id": prediction_id,
        "username": username,
        "submitted_by_patient": submitted_data,
        "prediction_output": output_data,
    }
    with open(PREDICTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_row) + "\n")


@app.post("/api/auth/register", response_model=AuthOut)
def register_user(data: AuthInput, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(username=username, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthOut(token=create_session_token(db, user.id), username=user.username)


@app.post("/api/auth/login", response_model=AuthOut)
def login_user(data: AuthInput, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return AuthOut(token=create_session_token(db, user.id), username=user.username)


@app.get("/api/auth/me")
def auth_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/auth/logout")
def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    token = parse_bearer_token(authorization)
    db.query(AuthSession).filter(AuthSession.token == token).delete()
    db.commit()
    return {"message": "Logged out"}


@app.get("/api/patients", response_model=dict)
def list_patients(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    outcome: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Patient)
    if outcome is not None:
        query = query.filter(Patient.outcome == outcome)

    total = query.count()
    rows = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "data": [PatientOut.model_validate(p) for p in rows],
    }


@app.get("/api/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    row = db.query(Patient).filter(Patient.id == patient_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return row


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Patient).count()
    diabetic = db.query(Patient).filter(Patient.outcome == 1).count()

    avg = db.query(
        func.avg(Patient.glucose),
        func.avg(Patient.bmi),
        func.avg(Patient.age),
        func.avg(Patient.blood_pressure),
        func.avg(Patient.insulin),
    ).one()

    return {
        "total_patients": total,
        "diabetic_count": diabetic,
        "non_diabetic_count": total - diabetic,
        "diabetic_percent": round(diabetic / total * 100, 1) if total else 0,
        "avg_glucose": round(avg[0] or 0, 1),
        "avg_bmi": round(avg[1] or 0, 1),
        "avg_age": round(avg[2] or 0, 1),
        "avg_blood_pressure": round(avg[3] or 0, 1),
        "avg_insulin": round(avg[4] or 0, 1),
    }


@app.get("/api/charts/distribution")
def chart_distribution(db: Session = Depends(get_db)):
    diabetic = db.query(Patient).filter(Patient.outcome == 1).count()
    non_diabetic = db.query(Patient).filter(Patient.outcome == 0).count()
    return {
        "labels": ["No Diabetes", "Diabetes"],
        "values": [non_diabetic, diabetic],
        "colors": ["#4ecdc4", "#ff6b6b"],
    }


@app.get("/api/charts/features")
def chart_features(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            outcome,
            AVG(glucose) as avg_glucose,
            AVG(bmi) as avg_bmi,
            AVG(age) as avg_age,
            AVG(blood_pressure) as avg_bp,
            AVG(insulin) as avg_insulin,
            AVG(pregnancies) as avg_pregnancies,
            AVG(dpf) as avg_dpf
        FROM patients
        GROUP BY outcome
        ORDER BY outcome
    """)).fetchall()

    labels = ["Glucose", "BMI", "Age", "Blood Pressure", "Insulin", "Pregnancies", "DPF"]
    no_diabetes = [0] * 7
    diabetes = [0] * 7

    for r in rows:
        values = [
            round(r[1] or 0, 1),
            round(r[2] or 0, 1),
            round(r[3] or 0, 1),
            round(r[4] or 0, 1),
            round(r[5] or 0, 1),
            round(r[6] or 0, 1),
            round(r[7] or 0, 3),
        ]
        if r[0] == 0:
            no_diabetes = values
        else:
            diabetes = values

    return {"labels": labels, "no_diabetes": no_diabetes, "diabetes": diabetes}


@app.get("/api/charts/glucose_histogram")
def chart_glucose(db: Session = Depends(get_db)):
    buckets = list(range(0, 220, 20))
    glucose_values = [row[0] for row in db.execute(text("SELECT glucose FROM patients")).fetchall() if row[0]]

    counts = [0] * (len(buckets) - 1)
    for value in glucose_values:
        for i in range(len(buckets) - 1):
            if buckets[i] <= value < buckets[i + 1]:
                counts[i] += 1
                break

    labels = [f"{buckets[i]}-{buckets[i + 1]}" for i in range(len(buckets) - 1)]
    return {"labels": labels, "counts": counts}


@app.get("/api/charts/bmi_histogram")
def chart_bmi(db: Session = Depends(get_db)):
    buckets = list(range(0, 75, 5))
    bmi_values = [row[0] for row in db.execute(text("SELECT bmi FROM patients")).fetchall() if row[0]]

    counts = [0] * (len(buckets) - 1)
    for value in bmi_values:
        for i in range(len(buckets) - 1):
            if buckets[i] <= value < buckets[i + 1]:
                counts[i] += 1
                break

    labels = [f"{buckets[i]}-{buckets[i + 1]}" for i in range(len(buckets) - 1)]
    return {"labels": labels, "counts": counts}


@app.get("/api/charts/feature_importance")
def chart_feature_importance():
    items = get_feature_importance()
    return {
        "labels": [item["feature"] for item in items],
        "values": [item["importance"] for item in items],
    }


@app.get("/api/model/accuracy")
def model_accuracy():
    acc = get_model_accuracy()
    return {"accuracy": acc, "model": "Random Forest"}


@app.get("/api/model/metrics")
def model_metrics():
    comparison = get_model_comparison()
    return {"models": comparison}


@app.post("/api/predict", response_model=PredictionOut)
def predict(
    data: PredictInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = data.model_dump()
    result = ml_model.predict(payload)

    # Save to predictions log table
    record = Prediction(
        user_id=user.id,
        **payload,
        prediction=result["prediction"],
        probability=result["probability"],
        risk_level=result["risk_level"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Also insert into patients table so stats/charts update immediately
    new_patient = Patient(
        pregnancies=int(round(payload["pregnancies"])),
        glucose=payload["glucose"],
        blood_pressure=payload["blood_pressure"],
        skin_thickness=payload["skin_thickness"],
        insulin=payload["insulin"],
        bmi=payload["bmi"],
        dpf=payload["dpf"],
        age=int(round(payload["age"])),
        outcome=result["prediction"],
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # Persist to diabetes.csv so the file stays in sync
    append_patient_to_csv(new_patient)

    append_prediction_log(payload, result, record.id, user.username)
    return record


@app.get("/api/predictions", response_model=dict)
def list_predictions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Prediction).filter(Prediction.user_id == user.id)
    total = query.count()
    rows = query.order_by(Prediction.id.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
        "data": [PredictionOut.model_validate(r) for r in rows],
    }


@app.get("/api/predictions/summary")
def prediction_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Prediction)
        .filter(Prediction.user_id == user.id)
        .order_by(Prediction.id.desc())
        .limit(2)
        .all()
    )

    latest = serialize_prediction(rows[0]) if len(rows) >= 1 else None
    previous = serialize_prediction(rows[1]) if len(rows) >= 2 else None
    probability_change = None

    if latest and previous:
        probability_change = round(latest["probability"] - previous["probability"], 1)

    return {
        "total_predictions": db.query(Prediction).filter(Prediction.user_id == user.id).count(),
        "latest": latest,
        "previous": previous,
        "probability_change": probability_change,
    }


@app.get("/api/predictions/{pred_id}", response_model=PredictionOut)
def get_prediction(
    pred_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(Prediction).filter(Prediction.id == pred_id, Prediction.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return row
