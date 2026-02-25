from app.mcp_instance import mcp
from app.services.email_service import email_service

@mcp.tool()
async def send_email(
    to: str,
    subject: str,
    body: str,
):
    """
    Send an email to a recipient.
    """
    return await email_service.send(to, subject, body)

