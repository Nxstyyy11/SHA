# Smart Healthcare Analytics

A full-stack diabetes risk analytics platform built with FastAPI, SQLite, scikit-learn, and a responsive dark-themed frontend — powered by ML.

## 🚀 Features

| Feature | Description |
|---|---|
| 📊 Dashboard Stats | Total patients, diabetic %, average glucose/BMI/age, model accuracy |
| 📈 Visual Charts | Outcome distribution, feature comparison, glucose histogram, BMI histogram |
| 🌲 Feature Importance | Random Forest feature importance horizontal bar chart |
| 🤖 Model Comparison | RF vs Logistic Regression — Accuracy, Precision, Recall, F1, AUC-ROC |
| 🔬 Risk Prediction | Real-time diabetes risk prediction with probability gauge |
| 💡 Health Tips | Personalised recommendations based on predicted risk level |
| ⚠️ Input Validation | Live range warnings for each clinical input field |
| 📋 Prediction History | Per-user history table with latest vs previous comparison |
| ⬇️ CSV Export | One-click download of your full prediction history |
| 🔐 Auth | Secure login/register with token-based sessions |

## 🛠️ Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **ML**: scikit-learn (RandomForestClassifier, LogisticRegression, StandardScaler)
- **Frontend**: Vanilla HTML/CSS/JavaScript + Chart.js
- **Auth**: PBKDF2-HMAC SHA-256 password hashing + secure session tokens

## 📁 Project Structure

```
smart-healthcare-analytics/
├── backend/
│   ├── main.py          # FastAPI routes & endpoints
│   ├── database.py      # SQLAlchemy models & DB init
│   ├── ml_model.py      # RF + LR training, metrics, feature importance
│   ├── diabetes_model.pkl
│   └── diabetes_scaler.pkl
├── frontend/
│   ├── index.html       # Single-page app
│   ├── app.js           # All frontend logic
│   └── style.css        # Dark glassmorphism theme
├── data/
│   └── diabetes.csv     # Pima Indians Diabetes Dataset (768 records)
├── notebooks/
│   └── 01_EDA.ipynb     # Exploratory Data Analysis
└── requirements.txt
```

## 📦 Setup & Run

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Start the server (from project root)
python run_project.py --dev

# Windows PowerShell alternative
./run_project.ps1 -Dev

# Linux/macOS alternative
./run_project.sh --dev

# 3. Open in browser
http://localhost:8000
```

## 🚀 Deploy (Render)

This project runs best on a platform that supports long-running FastAPI servers and persistent disk.

### Render Web Service Settings

- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `python run_project.py`

### Render Environment Variables

- `DATA_DIR=/opt/render/project/src/data`

### Render Disk

- Add a disk mount at `/opt/render/project/src/data`

### Notes

- Render provides a `$PORT` variable automatically. The app uses it.


## 📊 Dataset

**Pima Indians Diabetes Dataset** — National Institute of Diabetes and Digestive and Kidney Diseases  
- 768 patient records, 8 clinical features, binary outcome (diabetic / non-diabetic)
- Features: Pregnancies, Glucose, Blood Pressure, Skin Thickness, Insulin, BMI, Diabetes Pedigree Function, Age

## 🤖 ML Model

- **Primary**: Random Forest Classifier (100 estimators, max_depth=10, balanced weights)
- **Comparison**: Logistic Regression (max_iter=1000, balanced weights)
- **Preprocessing**: StandardScaler, median imputation for zero-value clinical fields
- **Evaluation**: Accuracy, Precision, Recall, F1-Score, AUC-ROC on 20% test split

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats` | Dataset summary statistics |
| GET | `/api/charts/distribution` | Outcome distribution |
| GET | `/api/charts/features` | Avg feature values by outcome |
| GET | `/api/charts/glucose_histogram` | Glucose distribution |
| GET | `/api/charts/bmi_histogram` | BMI distribution |
| GET | `/api/charts/feature_importance` | RF feature importances |
| GET | `/api/model/accuracy` | RF model accuracy |
| GET | `/api/model/metrics` | RF vs LR detailed metrics |
| POST | `/api/predict` | Diabetes risk prediction |
| GET | `/api/predictions` | User prediction history |
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User login |

## 📝 License

MIT
