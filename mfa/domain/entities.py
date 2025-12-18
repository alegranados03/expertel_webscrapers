from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmailBody(BaseModel):
    content_type: str = Field(alias="contentType")
    content: str

    model_config = {"populate_by_name": True}


class EmailAddress(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class EmailSender(BaseModel):
    email_address: EmailAddress = Field(alias="emailAddress")

    model_config = {"populate_by_name": True}


class EmailRecipient(BaseModel):
    email_address: EmailAddress = Field(alias="emailAddress")

    model_config = {"populate_by_name": True}


class EmailMessage(BaseModel):
    id: Optional[str] = None
    received_date_time: datetime = Field(alias="receivedDateTime")
    subject: str
    is_read: bool = Field(alias="isRead")
    body: EmailBody
    sender: Optional[EmailSender] = Field(default=None, alias="from")
    to_recipients: list[EmailRecipient] = Field(default_factory=list, alias="toRecipients")

    model_config = {"populate_by_name": True}


class InboxChecker(ABC):
    """Abstract base class for email inbox checkers.

    Implementations can be created for different email providers
    such as Outlook (Microsoft Graph API), Gmail, etc.
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the email provider.

        Returns:
            True if authentication was successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_messages(
        self,
        user_email: str,
        date_filter: datetime,
        top: int = 10,
        from_email: Optional[str] = None,
    ) -> list[EmailMessage] | None:
        """Retrieve messages from the inbox.

        Args:
            user_email: The email address of the mailbox to check.
            date_filter: Only return messages received after this datetime.
            top: Maximum number of messages to return.
            from_email: Optional filter to only return messages from this sender.

        Returns:
            List of EmailMessage objects, or None if an error occurred.
        """
        pass

    def display_messages(self, messages: list[EmailMessage]) -> None:
        """Display messages in a readable format.

        This is a concrete implementation that can be used by all subclasses,
        but can be overridden if needed.
        """
        if not messages:
            print("No messages to display")
            return

        print("\n" + "=" * 80)
        print("INBOX MESSAGES")
        print("=" * 80 + "\n")

        for i, msg in enumerate(messages, 1):
            print(f"Message #{i}")
            print(f"   Subject: {msg.subject}")

            if msg.sender:
                sender_name = msg.sender.email_address.name or "Unknown"
                sender_address = msg.sender.email_address.address or "N/A"
                print(f"   From: {sender_name} <{sender_address}>")

            if msg.to_recipients:
                print("   To (alias): ", end="")
                alias_list = [r.email_address.address or "N/A" for r in msg.to_recipients]
                print(", ".join(alias_list))

            print(f"   Received: {msg.received_date_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Status: {'Read' if msg.is_read else 'Unread'}")
            print("-" * 80 + "\n")
