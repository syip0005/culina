from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class AppSecrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OPENROUTER_API_KEY: str
    EXA_API_KEY: str


class AiSettings(BaseSettings):
    model_config = SettingsConfigDict(yaml_file="ai_settings.yaml")

    PRIMARY_LLM: Literal["google/gemini-3-flash-preview"] = (
        "google/gemini-3-flash-preview"
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        return (YamlConfigSettingsSource(settings_cls),)


secrets = AppSecrets()  # type: ignore[call-arg]
ai_settings = AiSettings()  # type: ignore[call-arg]
