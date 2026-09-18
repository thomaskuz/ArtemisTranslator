#!/usr/bin/env python3
"""
Simple AMQP 1.0 Consumer - Receives messages from Artemis
"""

from proton.handlers import MessagingHandler
from proton.reactor import Container
import json
import sys

class Consumer(MessagingHandler):
    """A class that handles receiving messages"""

    def __init__(self, url, source):
        super(Consumer, self).__init__()
        self.url = url
        self.source = source
        self.received_count = 0

    def on_start(self, event):
        """Called when container starts"""
        # Connect to the broker
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        # Create receiver for the address/queue
        event.container.create_receiver(event.connection, self.source)

    def on_link_opened(self, event):
        """Called when receiver link opens"""
        if event.receiver:
            print(f"[✓] Listening on: {self.source}")
            print(f"[!] Will receive ALL messages (historical + new)")
            print(f"[!] Press Ctrl+C to stop\n")

    def on_message(self, event):
        """Called when a message arrives"""
        self.received_count += 1
        message_body = event.message.body

        # Messages bridged in from MQTT arrive as raw AMQP binary (a memoryview),
        # not as a native AMQP string body - decode it before printing
        if isinstance(message_body, memoryview):
            message_body = bytes(message_body).decode('utf-8', errors='replace')

        print(f"[✓] Message {self.received_count} received:")
        try:
            payload = json.loads(message_body)
            print(f"    {json.dumps(payload, indent=2)}\n")
        except (json.JSONDecodeError, TypeError):
            print(f"    {message_body}\n")

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    # Configuration
    broker = "amqp://admin:admin@localhost:5672"
    address = "MQTT.AMQP.FAB.TEST"  # Multicast address
    queue = ""                      # Optional: specific queue under that address

    # "address::queue" binds to a specific queue (historical + new messages).
    # Leaving queue empty falls back to address-only, which only receives
    # NEW/real-time messages - see guides/amqp-multicast-anycast-behavior.md
    source = f"{address}::{queue}" if queue else address

    try:
        # Create consumer handler
        handler = Consumer(broker, source)

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
