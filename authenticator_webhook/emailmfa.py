import requests
import logging
import sys
import os
from datetime import datetime
from dotenv import find_dotenv, load_dotenv
from msal import ConfidentialClientApplication

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(sys.stdout),
#         logging.FileHandler('mfa.log', mode='a')
#     ]
# )

class OutlookInboxChecker:
    def __init__(self, client_id, tenant_id, client_secret):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self.access_token = None

    def get_access_token(self):
        """Gets the access token using Azure AD credentials"""
        AUTHORITY: str = f"https://login.microsoftonline.com/{self.tenant_id}"
        SCOPE: list[str] = [f"https://graph.microsoft.com/.default"]

        app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=AUTHORITY
        )
        try:
            token = app.acquire_token_for_client(scopes=SCOPE)
            if "access_token" not in token:
                raise RuntimeError(f"Token error: {token.get('error')} - {token.get('error_description')}")
            self.access_token = token["access_token"]
            print("✓ Access token obtained successfully")
            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Error getting access token: {e}")
            return False

    def get_messages(self, user_email, top=10, from_email=None):
        if not self.access_token:
            print("✗ You must first get the access token")
            return None

        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        filters=[
            "receivedDateTime ge ",
        ]
        params = {
            '$top': top,
            #'$filter': "from/emailAddress/address eq 'customerservice@iq.expertel.ca'",
            "$filter": (
                "receivedDateTime ge 2025-12-16T00:00:00Z "
                #"and from/emailAddress/address eq 'lawrence.coles@amarr.com' "
                "and toRecipients/emailAddress/address eq 'assaabloy@expertel.ca'"
            ),
            "$select": "subject,from,toRecipients,receivedDateTime,isRead",
            "$orderby": "receivedDateTime desc",
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            messages = response.json().get('value', [])
            print(f"✓ {len(messages)} messages obtained")
            return messages
        except requests.exceptions.RequestException as e:
            print(f"✗ Error getting messages: {e}")
            if response.text:
                print(f"Details: {response.text}")
            return None

    def display_messages(self, messages):
        """Displays messages in a readable format"""
        if not messages:
            print("No messages to display")
            return

        print("\n" + "=" * 80)
        print("INBOX MESSAGES")
        print("=" * 80 + "\n")

        for i, msg in enumerate(messages, 1):
            print(f"📧 Message #{i}")
            print(f"   Subject: {msg.get('subject', 'No subject')}")

            # Sender
            from_info = msg.get('from', {})
            from_email = from_info.get('emailAddress', {})
            print(f"   From: {from_email.get('name', 'Unknown')} <{from_email.get('address', 'N/A')}>")

            # Recipients (alias where email was received)
            recipients = msg.get('toRecipients', [])
            if recipients:
                print(f"   To (alias): ", end="")
                alias_list = [f"{r.get('emailAddress', {}).get('address', 'N/A')}" for r in recipients]
                print(", ".join(alias_list))

            # Date
            received = msg.get('receivedDateTime', '')
            if received:
                dt = datetime.fromisoformat(received.replace('Z', '+00:00'))
                print(f"   Received: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

            # Status
            is_read = msg.get('isRead', False)
            print(f"   Status: {'Read' if is_read else 'Unread'}")

            print("-" * 80 + "\n")


def main():
    # Configuration
    CLIENT_ID = os.environ.get("CLIENT_ID")
    TENANT_ID = os.environ.get("TENANT_ID")
    CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

    # Email of the user whose inbox you want to check
    USER_EMAIL = os.environ.get("USER_EMAIL")

    # Create checker instance
    checker = OutlookInboxChecker(CLIENT_ID, TENANT_ID, CLIENT_SECRET)

    # Get access token
    if not checker.get_access_token():
        print("\n⚠️  Could not get access token.")
        print("Verify that:")
        print("  1. The credentials are correct")
        print("  2. The application has the necessary permissions in Azure AD")
        print("  3. Application type permissions have been granted (not Delegated)")
        return

    # Get and display messages
    messages = checker.get_messages(USER_EMAIL, top=10)

    if messages:
        checker.display_messages(messages)
    else:
        print("\n⚠️  Could not get messages.")
        print("Verify that:")
        print("  1. The user email is correct")
        print("  2. The application has 'Mail.Read' or 'Mail.ReadWrite' permissions")
        print("  3. Administrator consent has been given to the permissions")


if __name__ == "__main__":
    main()