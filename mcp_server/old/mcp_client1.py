# mcp_client.py
import requests

BASE_URL = "http://localhost:8080"

def call_tool(tool_name: str, payload: dict):
    url = f"{BASE_URL}/tool/{tool_name}"
    
    response = requests.post(
        url,
        json={"payload": payload},
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")

    return response.json()


if __name__ == "__main__":
    # Example: call the "book_flight" tool
    flight_payload = {
        "from": "SFO",
        "to": "JFK",
        "date": "2026-03-01",
        "passenger_name": "John Doe"
    }

    result = call_tool("book_flight", flight_payload)
    print("Flight booking response:")
    print(result)

