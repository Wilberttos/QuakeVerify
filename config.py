import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    project_id: str = os.getenv("PROJECT_ID", "quakeverify_kelompok_01")
    mqtt_host: str = os.getenv("MQTT_HOST", "broker.hivemq.com")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "8883"))
    mqtt_tls: bool = os.getenv("MQTT_TLS", "true").lower() in ("true", "1", "yes")
    mqtt_ws_url: str = os.getenv("MQTT_WS_URL", "wss://broker.hivemq.com:8884/mqtt")
    http_port: int = int(os.getenv("HTTP_PORT", "8000"))

    def topic(self, suffix: str) -> str:
        return f"quakeverify/{self.project_id}/{suffix}"

settings = Settings()
