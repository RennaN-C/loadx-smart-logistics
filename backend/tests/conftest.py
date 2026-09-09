import os

# Keep application imports deterministic while production settings fail closed.
os.environ["APP_ENV"] = "local"
os.environ["SECRET_KEY"] = "loadx-test-secret-key-with-32-characters"
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost/loadx")
