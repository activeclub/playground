from google.cloud import storage
from google.oauth2 import service_account

from zenn_ai_agent.config import config

client = storage.Client(
    credentials=service_account.Credentials.from_service_account_file(
        config.service_account_key_path
    )
)
bucket = client.bucket(config.cloud_storage_bucket)
