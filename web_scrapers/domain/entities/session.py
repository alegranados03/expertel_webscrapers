from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SessionStatus(str, Enum):
    LOGGED_OUT = "logged_out"
    LOGGED_IN = "logged_in"
    ERROR = "error"


class Carrier(str, Enum):
    BELL = "Bell"
    TELUS = "Telus"
    ROGERS = "Rogers"
    ATT = "Att"
    TMOBILE = "T-Mobile"
    VERIZON = "verizon"


class Credentials(BaseModel):
    id: Optional[int] = None
    username: str
    password: str
    carrier: Carrier

    model_config = {"from_attributes": True}


class SessionState(BaseModel):
    status: SessionStatus = SessionStatus.LOGGED_OUT
    carrier: Optional[Carrier] = None
    credentials: Optional[Credentials] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}

    def is_logged_in(self) -> bool:
        return self.status == SessionStatus.LOGGED_IN

    def is_logged_out(self) -> bool:
        return self.status == SessionStatus.LOGGED_OUT

    def is_error(self) -> bool:
        return self.status == SessionStatus.ERROR

    def set_logged_in(self, carrier: Carrier, credentials: Credentials) -> None:
        self.status = SessionStatus.LOGGED_IN
        self.carrier = carrier
        self.credentials = credentials
        self.error_message = None

    def set_logged_out(self) -> None:
        self.status = SessionStatus.LOGGED_OUT
        self.error_message = None

    def set_error(self, error_message: str) -> None:
        self.status = SessionStatus.ERROR
        self.error_message = error_message
