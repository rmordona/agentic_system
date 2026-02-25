from app.mcp_instance import mcp
from app.services.booking_service import booking_service

@mcp.tool()
async def book_flight(
    from_airport: str,
    to_airport: str,
    date: str,
    passenger_name: str,
):
    """
    Book a flight between two airports for a passenger.
    """
    return await booking_service.book_flight(
        from_airport,
        to_airport,
        date,
        passenger_name,
    )

# Optional: attach parameter metadata manually
book_flight._metadata = {
    "parameters": [
        {"name": "from_airport", "type": "str"},
        {"name": "to_airport", "type": "str"},
        {"name": "date", "type": "str"},
        {"name": "passenger_name", "type": "str"},
    ]
}