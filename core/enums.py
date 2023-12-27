# ----- Generic imports --------------------------------------------------------
from enum import Enum
from django.utils.translation import gettext_lazy as _


class RoleEnum(Enum):
    ATHLETE = "Athlète"
    INSTRUCTOR = "Moniteur"
    # FSTB = Fédération Suisse de Twirling Bâton (Swiss Federation of Twirling Baton)
    FSTB_CC = "FSTB CC"  # FSTB Comité Central (FSTB Central Committee)
    FSTB_JUGES = "FSTB Juges"  # FSTB Juges (FSTB Judges)
    FSTB_CT = "FSTB CT"  # FSTB Commission Technique (FSTB Technical Commission)
    HELPER = "Membre libre"
    CLUB_ADMIN = "	Comité Club"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class ExamEnum(Enum):
    HONOR = "DH"
    FIRST_EXAM = "D1"
    SECOND_EXAM = "D2"
    THIRD_EXAM = "D3"
    FORTH_EXAM = "D4"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class JSEnum(Enum):
    MONITOR_JS = "Monitor J+S"
    MONITOR_JS_KIDS = "Monitor J+S Kids"
    EXPERT_JS = "Expert J+S"
    COACH_JS = "Coach J+S"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class GroupEnum(Enum):
    FSTB_ADMIN = "FSTB Admin"
    CLUB_ADMIN = "Club Admin"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class ChangeModelStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    DECLINED = "Declined"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class CompetitionRegistrationStatus(Enum):
    DRAFT = 'Draft'
    REGISTERED = 'Registered'
    FINISHED = 'Finished'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class CompetitionStatus(Enum):
    OPEN = 'Open'
    CLOSED = 'Closed'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class RuleCondition(Enum):
    GREATER = 'Greater'
    GREATER_OR_EQUAL = 'GreaterOrEqual'
    LESS_THAN = 'LessThan'
    LESS_THAN_OR_EQUAL = 'LessThanOrEqual'
    EQUAL = 'Equal'
    NOT_EQUAL = 'NotEqual'
    AVERAGE_EQUAL_TO = 'AverageEqualTo'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class RuleOption(Enum):
    YEAR = 'Year'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]
