from enum import Enum

class UserRole(str, Enum):
    AUTHOR = "AUTHOR"
    COORDINATOR = "COORDINATOR"
    MENTOR = "MENTOR"
