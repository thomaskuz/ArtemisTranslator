#!/usr/bin/env python3
"""
AMQP 1.0 Publisher with Headers - Sends messages with AMQP headers
"""

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys
import time

class PublisherWithHeaders(MessagingHandler):
    """Sends messages with AMQP headers"""

    def __init__(self, url, address):
        super(PublisherWithHeaders, self).__init__()
        self.url = url
        self.address = address
        self.sender = None
        self.message_count = 0
        self.last_send_time = 0
        self.reactor = None

    def on_start(self, event):
        """Called when container starts"""
        self.reactor = event.reactor
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        self.sender = event.container.create_sender(event.connection, self.address)

    def on_link_opened(self, event):
        """Called when sender link opens"""
        if event.sender:
            print(f"[✓] Sender ready for address: {self.address}")
            print(f"[!] Sending messages with headers every 5 seconds (Ctrl+C to stop)\n")
            self.last_send_time = time.time()
            self.send_message_with_headers()
            # Schedule next send
            if self.reactor:
                self.reactor.schedule(1.0, self)

    def send_message_with_headers(self):
        """Send a message with AMQP headers"""
        if self.sender:
            self.message_count += 1

            # Create message body
            body = f"Message #{self.message_count}: Test message with headers"

            # Create message object
            msg = Message(body=body)

            # Add AMQP headers (these are standard AMQP message properties)
            msg.id = f"msg-{self.message_count}"  # Message ID
            msg.reply_to = "reply-queue"           # Reply-to address
            msg.subject = "Test Subject"           # Subject
            msg.correlation_id = f"corr-{self.message_count}"  # Correlation ID

            # Add custom headers using message properties
            if not msg.properties:
                msg.properties = {}

            # Add custom application headers
            msg.properties["commander"] = "Thomas"
            msg.properties["custom_header_1"] = f"custom_value_{self.message_count}"
            msg.properties["custom_header_2"] = "application-specific-data"
            msg.properties["timestamp"] = str(time.time())

            # Send the message
            self.sender.send(msg)

            print(f"[✓] Sent message #{self.message_count}")
            print(f"    Body: {body}")
            print(f"    ID: {msg.id}")
            print(f"    Subject: {msg.subject}")
            print(f"    Correlation ID: {msg.correlation_id}")
            print(f"    Reply-to: {msg.reply_to}")
            print(f"    Custom headers: {dict(msg.properties)}\n")

            self.last_send_time = time.time()

    def on_timer_task(self, event):
        """Called by timer to check if we should send another message"""
        # Check if 5 seconds have passed since last send
        if time.time() - self.last_send_time >= 5:
            self.send_message_with_headers()

        # Schedule next check
        if self.reactor:
            self.reactor.schedule(1.0, self)

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    # Configuration
    broker = "amqp://admin:admin@localhost:5672"
    address = "amqp-mqtt-bridge"

    try:
        handler = PublisherWithHeaders(broker, address)
        container = Container(handler)

        print(f"[...] Starting publisher with headers (sending to {address})...\n")
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
