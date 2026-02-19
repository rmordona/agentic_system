from agents.tools from Tool

async def search_availability(query: str) -> dict:
    # External API call (non-deterministic)
    return {
        "available": True,
        "slots": ["2025-01-10", "2025-01-11"]
    }


class BookingTool(Tool):
    def __init__(self):
        super().__init__("booking_tool")

    async def run(self, args: dict, state: dict):
        # Simulate booking API call
        destination = args.get("destination", "Unknown")
        dates = args.get("dates", "N/A")
        return {
            "status": "success",
            "destination": destination,
            "dates": dates,
            "confirmation_number": "ABC123"
        }

