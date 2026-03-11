import sys

REQUIRED = [
    "pandas", "numpy", "matplotlib", "seaborn",
    "sklearn", "networkx", "flask", "joblib"
]

def check_packages():
    missing = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("❌ Missing packages:", ", ".join(missing))
        print("Install them using: pip install -r requirements.txt")
    else:
        print("✅ All required packages are installed!")

def test_versions():
    import pandas, numpy, sklearn
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Pandas version: {pandas.__version__}")
    print(f"Numpy version: {numpy.__version__}")
    print(f"Scikit-learn version: {sklearn.__version__}")

if __name__ == "__main__":
    check_packages()
    test_versions()
    print("\nEnvironment check complete.")
