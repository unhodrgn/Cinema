"""Load the canonical demo seed with explicit setup credentials."""
import os
from pathlib import Path

import psycopg2

from .set_demo_passwords import read_target


def main():
    target = read_target(os.environ)
    path = Path(__file__).resolve().parents[1] / "seeds" / "demo.sql"
    conn = psycopg2.connect(**target)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(path.read_text(encoding="utf-8"))
        print("Demo data loaded.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
