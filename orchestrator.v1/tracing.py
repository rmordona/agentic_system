import time

class Tracer:
    def event(self, name, **data):
        print({
            "event": name,
            "timestamp": time.time(),
            "data": data
        })

