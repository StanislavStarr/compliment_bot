"""seed topics qualities and fallback messages

Revision ID: d247b06bc2b6
Revises: c23ff31db2e4
Create Date: 2026-08-16 20:34:24.743917

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers, used by Alembic.
revision: str = "d247b06bc2b6"
down_revision: str | Sequence[str] | None = "c23ff31db2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Таблицы описаны локально (не импортируем ORM-модели в миграцию) — так
# сид не сломается при будущих изменениях моделей.
topics_table = sa.table(
    "topics",
    sa.column("id", PG_UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("label", sa.String),
)

qualities_table = sa.table(
    "qualities",
    sa.column("id", PG_UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("label", sa.String),
)

fallback_messages_table = sa.table(
    "fallback_messages",
    sa.column("id", PG_UUID(as_uuid=True)),
    sa.column("topic_code", sa.String),
    sa.column("type", PG_ENUM("COMPLIMENT", "SUPPORT", name="message_type", create_type=False)),
    sa.column(
        "address_mode", PG_ENUM("INFORMAL", "FORMAL", name="address_mode", create_type=False)
    ),
    sa.column("text", sa.String),
    sa.column("semantic_key", sa.String),
    sa.column("is_active", sa.Boolean),
)

TOPICS = [
    ("self_confidence", "Уверенность в себе"),
    ("character", "Черты характера"),
    ("self_care", "Забота о себе"),
    ("overcoming_difficulties", "Преодоление трудностей"),
    ("motivation", "Мотивация"),
    ("calm_and_acceptance", "Спокойствие и принятие"),
]

QUALITIES = [
    ("kindness", "Доброта"),
    ("honesty", "Честность"),
    ("resilience", "Стойкость"),
    ("sense_of_humor", "Чувство юмора"),
    ("empathy", "Эмпатия"),
    ("diligence", "Трудолюбие"),
    ("creativity", "Креативность"),
    ("courage", "Смелость"),
    ("patience", "Терпение"),
    ("responsibility", "Ответственность"),
    ("curiosity", "Любознательность"),
    ("generosity", "Щедрость"),
]

# (topic_code, type, semantic_key, text_informal, text_formal)
FALLBACK_MESSAGES = [
    (
        "self_confidence",
        "compliment",
        "опора на себя в решениях",
        "Ты умеешь опираться на себя даже тогда, когда решения даются непросто — "
        "это редкое качество характера.",
        "Вы умеете опираться на себя даже тогда, когда решения даются непросто — "
        "это редкое качество характера.",
    ),
    (
        "self_confidence",
        "support",
        "внутренняя опора при неуверенности",
        "Даже если сегодня было трудно поверить в себя, внутри у тебя есть опора, "
        "на которую можно вернуться.",
        "Даже если сегодня было трудно поверить в себя, внутри у вас есть опора, "
        "на которую можно вернуться.",
    ),
    (
        "character",
        "compliment",
        "мягкость и твёрдость характера",
        "В тебе сочетаются мягкость и внутренняя твёрдость — с тобой рядом становится спокойнее.",
        "В вас сочетаются мягкость и внутренняя твёрдость — с вами рядом становится спокойнее.",
    ),
    (
        "character",
        "support",
        "ценность характера без безупречности",
        "Твой характер не обязан быть безупречным каждый день, чтобы оставаться по-настоящему ценным.",
        "Ваш характер не обязан быть безупречным каждый день, чтобы оставаться по-настоящему ценным.",
    ),
    (
        "self_care",
        "compliment",
        "забота о себе как тихая сила",
        "Ты умеешь замечать, когда пора остановиться и позаботиться о себе — "
        "это тихая, но важная сила.",
        "Вы умеете замечать, когда пора остановиться и позаботиться о себе — "
        "это тихая, но важная сила.",
    ),
    (
        "self_care",
        "support",
        "забота о себе не слабость",
        "Забота о себе сегодня — это не слабость, а важный способ остаться в контакте с собой.",
        "Забота о себе сегодня — это не слабость, а важный способ остаться в контакте с собой.",
    ),
    (
        "overcoming_difficulties",
        "compliment",
        "устойчивость через прошлый опыт",
        "Ты уже проходил через непростые моменты и находил дорогу дальше — "
        "это говорит о внутренней устойчивости.",
        "Вы уже проходили через непростые моменты и находили дорогу дальше — "
        "это говорит о внутренней устойчивости.",
    ),
    (
        "overcoming_difficulties",
        "support",
        "прошлый опыт преодоления трудностей",
        "Если сейчас трудно, это не отменяет того, что раньше ты уже справлялся со сложными периодами.",
        "Если сейчас трудно, это не отменяет того, что раньше вы уже справлялись со сложными периодами.",
    ),
    (
        "motivation",
        "compliment",
        "внутренний огонёк для движения",
        "В тебе есть внутренний огонёк, который помогает двигаться дальше даже в медленные дни.",
        "В вас есть внутренний огонёк, который помогает двигаться дальше даже в медленные дни.",
    ),
    (
        "motivation",
        "support",
        "малое движение имеет значение",
        "Даже небольшое движение вперёд сегодня уже имеет значение, даже если оно незаметно снаружи.",
        "Даже небольшое движение вперёд сегодня уже имеет значение, даже если оно незаметно снаружи.",
    ),
    (
        "calm_and_acceptance",
        "compliment",
        "спокойная зрелость принятия",
        "Ты умеешь принимать вещи такими, какие они есть, без лишней борьбы с собой — "
        "в этом есть спокойная зрелость.",
        "Вы умеете принимать вещи такими, какие они есть, без лишней борьбы с собой — "
        "в этом есть спокойная зрелость.",
    ),
    (
        "calm_and_acceptance",
        "support",
        "не всё нужно контролировать сейчас",
        "Не всё нужно объяснять или контролировать прямо сейчас — "
        "иногда достаточно просто побыть в моменте.",
        "Не всё нужно объяснять или контролировать прямо сейчас — "
        "иногда достаточно просто побыть в моменте.",
    ),
]


def upgrade() -> None:
    op.bulk_insert(
        topics_table,
        [{"id": uuid.uuid4(), "code": code, "label": label} for code, label in TOPICS],
    )
    op.bulk_insert(
        qualities_table,
        [{"id": uuid.uuid4(), "code": code, "label": label} for code, label in QUALITIES],
    )

    fallback_rows = []
    for topic_code, msg_type, semantic_key, text_informal, text_formal in FALLBACK_MESSAGES:
        fallback_rows.append(
            {
                "id": uuid.uuid4(),
                "topic_code": topic_code,
                "type": msg_type.upper(),
                "address_mode": "INFORMAL",
                "text": text_informal,
                "semantic_key": semantic_key,
                "is_active": True,
            }
        )
        fallback_rows.append(
            {
                "id": uuid.uuid4(),
                "topic_code": topic_code,
                "type": msg_type.upper(),
                "address_mode": "FORMAL",
                "text": text_formal,
                "semantic_key": semantic_key,
                "is_active": True,
            }
        )
    op.bulk_insert(fallback_messages_table, fallback_rows)


def downgrade() -> None:
    op.execute(fallback_messages_table.delete())
    op.execute(qualities_table.delete())
    op.execute(topics_table.delete())
