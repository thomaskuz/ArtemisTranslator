#!/usr/bin/env python3
"""
AMQP 1.0 Consumer with Selector Filter - Receives filtered messages from Artemis
Demonstrates AMQP selector filters (similar to JMS message selectors)
"""

from proton.handlers import MessagingHandler
from proton.reactor import Container
from proton import Symbol
import sys

class ConsumerWithFilter(MessagingHandler):
    """A class that handles receiving filtered messages"""

    def __init__(self, url, queue, filter_expression=None):
        super(ConsumerWithFilter, self).__init__()
        self.url = url
        self.queue = queue
        self.filter_expression = filter_expression
        self.received_count = 0
        self.receiver = None

    def on_start(self, event):
        """Called when container starts"""
        # Connect to the broker
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")

        # Create receiver for the queue with optional filter
        receiver_opts = None
        if self.filter_expression:
            # Set up AMQP selector filter
            # Filter expression uses application properties
            receiver_opts = "selector: %s" % self.filter_expression
            print(f"[!] Using filter: {self.filter_expression}")

        self.receiver = event.container.create_receiver(
            event.connection,
            self.queue,
            options=receiver_opts
        )

    def on_link_opened(self, event):
        """Called when receiver link opens"""
        if event.receiver:
            print(f"[✓] Listening on queue: {self.queue}")
            if self.filter_expression:
                print(f"[!] Filter applied: {self.filter_expression}")
            else:
                print(f"[!] No filter - receiving ALL messages")
            print(f"[!] Will receive historical + new messages")
            print(f"[!] Press Ctrl+C to stop\n")

    def on_message(self, event):
        """Called when a message arrives"""
        self.received_count += 1
        message_body = event.message.body

        print(f"[✓] Message {self.received_count} received:")

        # Display properties if available
        if hasattr(event.message, 'properties') and event.message.properties:
            print(f"    Properties: {dict(event.message.properties)}")

        print(f"    Body: {message_body}\n")

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    # Configuration
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test"  # Queue name

    # Optional: Set a filter expression
    # AMQP Selector Syntax (similar to JMS message selectors):
    #
    # Examples:
    # "commander = 'Thomas'"                    # Exact match
    # "message_number > 5"                      # Numeric comparison
    # "commander = 'Thomas' AND message_number > 3"  # AND logic
    # "commander = 'Thomas' OR commander = 'Alice'"  # OR logic
    # "NOT commander = 'Bob'"                   # NOT logic
    # "commander LIKE 'Th%'"                    # Pattern matching
    #
    # Note: String values must use single quotes (not double quotes)

    # Uncomment one of these to enable filtering:
    filter_expr = None  # No filter - get all messages
    # filter_expr = "commander = 'Thomas'"      # Only Thomas messages
    # filter_expr = "message_number > 5"        # Only messages > 5
    # filter_expr = "commander IN ('Thomas', 'Alice')"  # Multiple values

    try:
        # Create consumer handler with optional filter
        handler = ConsumerWithFilter(broker, queue, filter_expr)

        # Create and run container
        container = Container(handler)
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
