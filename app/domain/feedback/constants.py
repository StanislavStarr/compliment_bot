from app.domain.profiles.enums import DislikeReason

DISLIKE_REASON_LABELS: dict[DislikeReason, str] = {
    DislikeReason.TOO_TEMPLATED: "Слишком шаблонно",
    DislikeReason.TOO_SWEET: "Слишком пафосно или приторно",
    DislikeReason.UNNATURAL: "Звучит неестественно",
    DislikeReason.DOES_NOT_FIT: "Не соответствует мне",
    DislikeReason.UNPLEASANT_WORDING: "Неприятная формулировка",
    DislikeReason.WRONG_TOPIC: "Не подходит выбранной теме",
    DislikeReason.OTHER: "Другая причина",
}
