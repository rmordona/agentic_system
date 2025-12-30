class HumanApproval:
    def __init__(self, enabled=False):
        self.enabled = enabled

    def approve(self, decision):
        if not self.enabled:
            return True

        print("PROPOSED DECISION:")
        print(decision)
        response = input("Approve? (y/n): ")
        return response.lower().startswith("y")

