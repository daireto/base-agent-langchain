from typing import Literal

from dotenv import find_dotenv
from langchain.chat_models import BaseChatModel, init_chat_model
from pydantic import BaseModel, Secret, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatModelSettings(BaseModel):
    model: str = 'gpt-4o-mini'
    temperature: float = 0.2
    max_tokens: int = 2000
    timeout: int = 30
    max_retries: int = 3
    base_url: str | None = None

    def init_chat_model(self) -> BaseChatModel:
        return init_chat_model(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=self.max_retries,
            base_url=self.base_url,
        )


class DatabaseConfig(BaseModel):
    url: Secret[str] = Secret('sqlite+aiosqlite:///.conversations.sqlite')


class MemoriesConfig(BaseModel):
    collection_name: str = 'memories'


class RestServerConfig(BaseModel):
    env: Literal['dev', 'prod'] = 'dev'
    port: int = 8000
    host: str = 'localhost'
    debug: bool = False
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None
    allowed_hosts: str = '*'
    behind_proxy: bool = False

    @property
    def is_dev(self) -> bool:
        return self.env == 'dev'

    @property
    def is_prod(self) -> bool:
        return self.env == 'prod'

    @property
    def https(self) -> bool:
        return self.ssl_certfile is not None and self.ssl_keyfile is not None

    @property
    def scheme(self) -> Literal['http', 'https']:
        return 'https' if self.https else 'http'

    @property
    def base_url(self) -> str:
        return f'{self.scheme}://{self.host}:{self.port}'

    @property
    def swagger_url(self) -> str:
        return f'{self.base_url}/docs'

    @property
    def redoc_url(self) -> str:
        return f'{self.base_url}/redoc'

    @property
    def startup_msg(self) -> str:
        return (
            f'App started in {self.env} mode.'
            f' Listening on port {self.port}.'
            f' Docs available at {self.swagger_url} and {self.redoc_url}'
        )


class RestCORSConfig(BaseModel):
    allow_origins: str = '*'
    allow_methods: str = '*'
    allow_headers: str = 'X-Requested-With,X-Request-ID'
    expose_headers: str = 'X-Request-ID'


class RestLogConfig(BaseModel):
    path: str | None = None
    access_log_excluded_path_prefixes: str = 'openapi.json,docs,redoc,health,admin'


class RestRateLimitConfig(BaseModel):
    storage_uri: Secret[str] = Secret('memory://')
    root_limit: str = '5/second'


class RunnableConfig(BaseModel):
    max_concurrency: int = 10
    max_recursion_limit: int = 25


class SupervisorConfig(ChatModelSettings):
    checkpointer_url: Secret[str] = Secret('.checkpoints.sqlite')


class UefaRagConfig(BaseModel):
    embeddings_model: str = 'text-embedding-3-small'
    collection_name: str = 'uefa_docs'


class ChromaConfig(BaseModel):
    mode: Literal['local', 'server'] = 'local'
    local_db_path: str = '.chroma_db'
    host: str = 'localhost'
    port: int = 8001
    ssl: bool = False
    api_token: SecretStr = SecretStr('my-secret-token')


class QdrantConfig(BaseModel):
    mode: Literal['local', 'server'] = 'local'
    local_db_path: str = '.qdrant_db'
    url: str = 'http://localhost:6333'
    timeout: int = 30
    api_key: SecretStr = SecretStr('my-secret-token')


class Settings(BaseSettings):
    presentation_mode: Literal['a2a', 'rest', 'ui'] = 'ui'

    langfuse_enabled: bool = False

    virustotal_api_key: SecretStr
    abuseipdb_api_key: SecretStr

    supervisor: SupervisorConfig = SupervisorConfig()
    soc_agent: ChatModelSettings = ChatModelSettings()
    uefa_agent: ChatModelSettings = ChatModelSettings()
    summarization: ChatModelSettings = ChatModelSettings()
    memory_extractor: ChatModelSettings = ChatModelSettings()
    database: DatabaseConfig = DatabaseConfig()
    memories: MemoriesConfig = MemoriesConfig()
    rest_server: RestServerConfig = RestServerConfig()
    rest_cors: RestCORSConfig = RestCORSConfig()
    rest_log: RestLogConfig = RestLogConfig()
    rest_rate_limit: RestRateLimitConfig = RestRateLimitConfig()
    runnable: RunnableConfig = RunnableConfig()
    uefa_rag: UefaRagConfig = UefaRagConfig()
    chroma: ChromaConfig = ChromaConfig()
    qdrant: QdrantConfig = QdrantConfig()

    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        env_file_encoding='utf-8',
        case_sensitive=False,
        env_nested_delimiter='__',
        env_nested_max_split=1,
        extra='ignore',
    )


settings = Settings()  # type: ignore
