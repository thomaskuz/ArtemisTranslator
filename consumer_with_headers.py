#!/usr/bin/env python3
"""
AMQP 1.0 Consumer with Headers - Receives and displays AMQP headers
"""

from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys

class ConsumerWithHeaders(MessagingHandler):
    """Receives and displays AMQP headers"""

    def __init__(self, url, queue):
        super(ConsumerWithHeaders, self).__init__()
        self.url = url
        self.queue = queue
        self.received_count = 0

    def on_start(self, event):
        """Called when container starts"""
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        event.container.create_receiver(event.connection, self.queue)

    def on_link_opened(self, event):
        """Called when receiver link opens"""
        if event.receiver:
            print(f"[✓] Listening on queue: {self.queue}")
            print(f"[!] Press Ctrl+C to stop\n")

    def on_message(self, event):
        """Called when a message arrives"""
        self.received_count += 1
        msg = event.message

        print(f"\n{'='*60}")
        print(f"[✓] Message #{self.received_count} received:")
        print(f"{'='*60}")

        # Display body
        print(f"\nBody:")
        print(f"  {msg.body}")

        # Display AMQP message properties/headers
        print(f"\nAMQP Headers:")
        print(f"  Message ID: {msg.id}")
        print(f"  Subject: {msg.subject}")
        print(f"  Correlation ID: {msg.correlation_id}")
        print(f"  Reply-to: {msg.reply_to}")
        print(f"  Content Type: {msg.content_type}")
        print(f"  Content Encoding: {msg.content_encoding}")
        print(f"  Timestamp: {msg.timestamp}")
        print(f"  TTL (Time-to-live): {msg.ttl}")
        print(f"  Priority: {msg.priority}")
        print(f"  User ID: {msg.user_id}")

        # Display custom application properties
        if msg.properties:
            print(f"\nCustom Application Headers:")
            for key, value in msg.properties.items():
                print(f"  {key}: {value}")
        else:
            print(f"\nCustom Application Headers: (none)")

        # Display delivery annotations (Artemis-specific)
        if msg.annotations:
            print(f"\nDelivery Annotations:")
            for key, value in msg.annotations.items():
                print(f"  {key}: {value}")
        else:
            print(f"\nDelivery Annotations: (none)")

        print(f"{'='*60}\n")

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    # Configuration
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"

    try:
        handler = ConsumerWithHeaders(broker, queue)
        container = Container(handler)

        print(f"[...] Starting consumer with headers (listening to {queue})...\n")
        container.run()

    except KeyboardInterrupt:
        print(f"\n[!] Stopped by user")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
