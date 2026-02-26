import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wakou.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
