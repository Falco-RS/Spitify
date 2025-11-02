from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = ".venv"
    database_url: str
    jwt_secret: str
    jwt_exp_min: int = 240

    media_root: str = "./media"
    node_name: str = "worker-1"

    coord_url: str = "http://127.0.0.1:8000" 
    heartbeat_sec: int = 3 
    ffmpeg_path: str = ""
    public_base_url: str = "http://127.0.0.1:8000"

    class Config:
        env_file = ".env"

settings = Settings()
