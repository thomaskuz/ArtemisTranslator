#!/usr/bin/env python3
"""
AMQP 1.0 Publisher - Sends messages to Artemis every 5 seconds
"""

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys
import time

class Publisher(MessagingHandler):
    """A class that handles sending messages"""

    def __init__(self, url, queue, message_template):
        super(Publisher, self).__init__()
        self.url = url
        self.queue = queue
        self.message_template = message_template
        self.sender = None
        self.message_count = 0
        self.last_send_time = 0

    def on_start(self, event):
        """Called when container starts"""
        # Connect to the broker
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        # Create sender for the queue
        self.sender = event.container.create_sender(event.connection, self.queue)

    def on_link_opened(self, event):
        """Called when sender link opens"""
        if event.sender:
            print(f"[✓] Sender ready for queue: {self.queue}")
            print(f"[!] Sending messages every 5 seconds (Ctrl+C to stop)\n")
            # Schedule first message immediately
            self.last_send_time = time.time()
            self.send_message()

    def send_message(self):
        """Send a message to the queue"""
        if self.sender:
            self.message_count += 1
            # Create message with counter
            message_text = f"{self.message_template} (#{self.message_count})"
            msg = Message(body=message_text)
            self.sender.send(msg)
            print(f"[✓] Sent message #{self.message_count}: {message_text}")
            self.last_send_time = time.time()

    def on_timer_task(self, event):
        """Called by timer to check if we should send another message"""
        # Check if 5 seconds have passed since last send
        if time.time() - self.last_send_time >= 5:
            self.send_message()

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    # Configuration
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"
    message_template = "Hello from Artemis"

    try:
        # Create publisher handler
        handler = Publisher(broker, queue, message_template)

        # Create and run container
        container = Container(handler)

        # Schedule timer that checks every 1 second if we should send
        container.schedule(1.0, handler)

        print(f"[...] Starting publisher (sending to {queue})...")
        container.run()

    except KeyboardInterrupt:
        print(f"\n[!] Stopped by user")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
