import argparse
import os
import sys

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Smart Healthcare Analytics server")
    parser.add_argument("--dev", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=args.dev,
    )


if __name__ == "__main__":
    sys.exit(main())
