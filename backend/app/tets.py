from sqlalchemy import text
from sqlalchemy import create_engine

from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            print("✅ Conexión exitosa a PostgreSQL")
            print("Versión:", result.scalar())
    except Exception as e:
        print("❌ Error de conexión:", e)

if __name__ == "__main__":
    test_connection()
