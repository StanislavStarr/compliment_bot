from enum import StrEnum


class StyleExampleSource(StrEnum):
    ONBOARDING = "onboarding"
    LIKED_MESSAGE = "liked_message"


class DislikeReason(StrEnum):
    TOO_TEMPLATED = "too_templated"
    TOO_SWEET = "too_sweet"
    UNNATURAL = "unnatural"
    DOES_NOT_FIT = "does_not_fit"
    UNPLEASANT_WORDING = "unpleasant_wording"
    WRONG_TOPIC = "wrong_topic"
    OTHER = "other"
