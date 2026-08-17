#!/usr/bin/env python3
"""
Simple AMQP 1.0 Consumer - Receives messages from Artemis
"""

from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys

class Consumer(MessagingHandler):
    """A class that handles receiving messages"""

    def __init__(self, url, queue):
        super(Consumer, self).__init__()
        self.url = url
        self.queue = queue
        self.received_count = 0

    def on_start(self, event):
        """Called when container starts"""
        # Connect to the broker
        event.container.connect(self.url)
        print("on_start called")

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        # Create receiver for the queue
        event.container.create_receiver(event.connection, self.queue)
        print("on_connection_opened called")

    def on_link_opened(self, event):
        """Called when receiver link opens"""
        if event.receiver:
            print(f"[✓] Listening on queue: {self.queue}")
            print(f"[!] Press Ctrl+C to stop\n")
            print("on_link_opened called")

    def on_message(self, event):
        """Called when a message arrives"""
        self.received_count += 1
        message_body = event.message.body
        print("on_message called")

        print(f"[✓] Message {self.received_count} received:")
        print(f"    {message_body}\n")

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    # Configuration
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"

    try:
        # Create consumer handler
        handler = Consumer(broker, queue)

        # Create and run container
        container = Container(handler)
        container.run()

    except KeyboardInterrupt:
        print(f"\n[!] Stopped by user")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
