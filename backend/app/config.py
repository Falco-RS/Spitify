from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = ".venv"
    database_url: str
    jwt_secret: str
    jwt_exp_min: int = 240

    class Config:
        env_file = ".env"

settings = Settings()
