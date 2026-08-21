#!/usr/bin/env python3
"""
Simple AMQP Publisher - Alternating commanders for filter testing
Sends messages alternating between two commander values to test filters
"""

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys
import time
import json

class SimplePublisherAlternating(MessagingHandler):
    """Sends messages with alternating commander values"""

    def __init__(self, url, queue):
        super(SimplePublisherAlternating, self).__init__()
        self.url = url
        self.queue = queue
        self.sender = None
        self.message_count = 0
        self.last_send_time = 0
        self.reactor = None
        # Alternate between these commanders
        self.commanders = ["Thomas", "Alice"]

    def on_start(self, event):
        """Called when container starts"""
        self.reactor = event.reactor
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        self.sender = event.container.create_sender(event.connection, self.queue)

    def on_link_opened(self, event):
        """Called when sender link opens"""
        if event.sender:
            print(f"[✓] Sender ready for queue: {self.queue}")
            print(f"[!] Sending messages with alternating commanders every 5 seconds (Ctrl+C to stop)")
            print(f"[!] Commanders: {', '.join(self.commanders)}\n")
            self.last_send_time = time.time()
            self.send_alternating_message()
            if self.reactor:
                self.reactor.schedule(1.0, self)

    def send_alternating_message(self):
        """Send a message with alternating commander"""
        if self.sender:
            self.message_count += 1

            # Alternate commander based on message count
            commander = self.commanders[self.message_count % len(self.commanders)]

            # Create message body as JSON with alternating commander
            body_dict = {
                "commander": commander,
                "message_number": self.message_count,
                "sequence": (self.message_count // len(self.commanders)) + 1
            }
            body = json.dumps(body_dict)

            # Create and send message
            msg = Message(body=body)
            self.sender.send(msg)

            print(f"[✓] Sent message #{self.message_count}")
            print(f"    Commander: {commander}")
            print(f"    Body: {body}\n")

            self.last_send_time = time.time()

    def on_timer_task(self, event):
        """Called by timer to check if we should send another message"""
        if time.time() - self.last_send_time >= 5:
            self.send_alternating_message()

        if self.reactor:
            self.reactor.schedule(1.0, self)

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"

    try:
        handler = SimplePublisherAlternating(broker, queue)
        container = Container(handler)

        print(f"[...] Starting alternating publisher (sending to {queue})...\n")
        container.run()

    except KeyboardInterrupt:
        print(f"\n[!] Stopped by user")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
