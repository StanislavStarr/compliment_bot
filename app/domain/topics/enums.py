from enum import StrEnum


class TopicCode(StrEnum):
    SELF_CONFIDENCE = "self_confidence"
    CHARACTER = "character"
    SELF_CARE = "self_care"
    OVERCOMING_DIFFICULTIES = "overcoming_difficulties"
    MOTIVATION = "motivation"
    CALM_AND_ACCEPTANCE = "calm_and_acceptance"


MAX_ACTIVE_TOPICS_PER_USER = 3
