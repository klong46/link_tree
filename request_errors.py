class RequestErrors:
    def __init__(self):
        self.messages = []

    def print_num(self):
        print(f"FAILURES: {len(self.messages)}")

    def add_error(self, error_message):
        self.messages.append(error_message)