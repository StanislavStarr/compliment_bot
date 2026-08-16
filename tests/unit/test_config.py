from app.config import Settings


def test_database_url_built_from_components() -> None:
    settings = Settings(
        postgres_user="u",
        postgres_password="p",  # noqa: S106
        postgres_host="db-host",
        postgres_port=5433,
        postgres_db="mydb",
    )

    assert settings.database_url == "postgresql+asyncpg://u:p@db-host:5433/mydb"


def test_redis_and_celery_urls_use_separate_db_indexes() -> None:
    settings = Settings(redis_host="redis-host", redis_port=6380, redis_db=0)

    assert settings.redis_url == "redis://redis-host:6380/0"
    assert settings.celery_broker_url == "redis://redis-host:6380/1"
    assert settings.celery_result_backend == "redis://redis-host:6380/2"
