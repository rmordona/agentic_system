import os
from datetime import timedelta

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "refreshsecretkey")
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://jonthsmith:welcome1@localhost:5432/context_platform")
