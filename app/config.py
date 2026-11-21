from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_api_key: str
    llm_model: str = "gemini-3.5-flash-lite"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 6

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
