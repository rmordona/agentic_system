class EmailService:

    async def send(self, to: str, subject: str, body: str):
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
        }

email_service = EmailService()

