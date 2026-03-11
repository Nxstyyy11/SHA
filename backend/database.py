"""
Database setup and initialization for Smart Healthcare Analytics
"""
import csv
import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, text
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker

# Database path (one level up in data/ folder, or /tmp on Vercel)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.getenv("VERCEL"))
if IS_VERCEL:
    DATA_DIR = os.path.join("/tmp", "smart_healthcare_analytics")
else:
    DATA_DIR = os.path.join(BASE_DIR, "..", "data")

DB_PATH = os.path.join(DATA_DIR, "healthcare.db")
CSV_PATH = os.path.join(DATA_DIR, "diabetes.csv")

os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    pregnancies = Column(Integer)
    glucose = Column(Float)
    blood_pressure = Column(Float)
    skin_thickness = Column(Float)
    insulin = Column(Float)
    bmi = Column(Float)
    dpf = Column(Float)  # DiabetesPedigreeFunction
    age = Column(Integer)
    outcome = Column(Integer)  # 0 = no diabetes, 1 = diabetes


class Prediction(Base):
    """Stores every prediction request + result for audit / history."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, index=True, nullable=True)
    # Input features
    pregnancies    = Column(Float)
    glucose        = Column(Float)
    blood_pressure = Column(Float)
    skin_thickness = Column(Float)
    insulin        = Column(Float)
    bmi            = Column(Float)
    dpf            = Column(Float)
    age            = Column(Float)
    # Model output
    prediction     = Column(Integer)   # 0 or 1
    probability    = Column(Float)     # 0-100
    risk_level     = Column(String)    # Low / Medium / High
    created_at     = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables and load CSV data if database is empty."""
    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM patients"))
        count = result.scalar()

    if count == 0:
        print("Loading diabetes dataset into database...")
        if not os.path.exists(CSV_PATH):
            _create_sample_data()

        df = pd.read_csv(CSV_PATH)
        # Normalize column names
        col_map = {
            "Pregnancies": "pregnancies",
            "Glucose": "glucose",
            "BloodPressure": "blood_pressure",
            "SkinThickness": "skin_thickness",
            "Insulin": "insulin",
            "BMI": "bmi",
            "DiabetesPedigreeFunction": "dpf",
            "Age": "age",
            "Outcome": "outcome",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        df.to_sql("patients", engine, if_exists="append", index=False)
        print(f"Loaded {len(df)} patient records.")
    else:
        print(f"Database already has {count} records.")


def _ensure_schema_compatibility():
    """Add columns needed by newer versions without wiping existing data."""
    with engine.connect() as conn:
        cols = conn.execute(text("PRAGMA table_info(predictions)")).fetchall()
        col_names = {c[1] for c in cols}
        if "user_id" not in col_names:
            conn.execute(text("ALTER TABLE predictions ADD COLUMN user_id INTEGER"))
            conn.commit()


def _create_sample_data():
    """Create a sample diabetes CSV if one doesn't exist."""
    import numpy as np

    np.random.seed(42)
    n = 768

    data = {
        "Pregnancies": np.random.randint(0, 18, n),
        "Glucose": np.random.randint(0, 200, n),
        "BloodPressure": np.random.randint(0, 122, n),
        "SkinThickness": np.random.randint(0, 100, n),
        "Insulin": np.random.randint(0, 846, n),
        "BMI": np.round(np.random.uniform(0, 67.1, n), 1),
        "DiabetesPedigreeFunction": np.round(np.random.uniform(0.078, 2.42, n), 3),
        "Age": np.random.randint(21, 81, n),
    }
    # Simple rule-based outcome
    glucose = data["Glucose"]
    bmi = data["BMI"]
    age = data["Age"]
    outcome = ((glucose > 120) & (bmi > 30)).astype(int)
    # Add some noise
    flip = np.random.rand(n) < 0.15
    outcome[flip] = 1 - outcome[flip]
    data["Outcome"] = outcome

    df = pd.DataFrame(data)
    df.to_csv(CSV_PATH, index=False)
    print(f"Created sample data at {CSV_PATH}")


def append_patient_to_csv(patient: "Patient"):
    """Append a newly predicted patient record to diabetes.csv."""
    row = {
        "Pregnancies": patient.pregnancies,
        "Glucose": patient.glucose,
        "BloodPressure": patient.blood_pressure,
        "SkinThickness": patient.skin_thickness,
        "Insulin": patient.insulin,
        "BMI": patient.bmi,
        "DiabetesPedigreeFunction": patient.dpf,
        "Age": patient.age,
        "Outcome": patient.outcome,
    }
    file_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    print(f"Appended patient (id={patient.id}) to {CSV_PATH}")
