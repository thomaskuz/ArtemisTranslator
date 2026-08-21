#!/usr/bin/env python3
"""
AMQP 1.0 Publisher - Extended Headers & Metadata
Demonstrates all types of message metadata and where they appear in Artemis
"""

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys
import time

class PublisherExtended(MessagingHandler):
    """Sends messages with all types of AMQP metadata"""

    def __init__(self, url, address):
        super(PublisherExtended, self).__init__()
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
            print(f"[!] Sending messages with extended headers (Ctrl+C to stop)\n")
            self.last_send_time = time.time()
            self.send_message_extended()
            # Schedule next send
            if self.reactor:
                self.reactor.schedule(1.0, self)

    def send_message_extended(self):
        """Send a message with all types of AMQP metadata"""
        if self.sender:
            self.message_count += 1

            # ========================================
            # MESSAGE BODY
            # ========================================
            body = f"Extended message #{self.message_count} with all metadata types"

            # Create message object
            msg = Message(body=body)

            # ========================================
            # AMQP MESSAGE PROPERTIES
            # Visual Section: Properties
            # Logical Type: Standard AMQP Message Properties (properties.*)
            # These are standard AMQP 1.0 message properties
            # ========================================

            # Message identifier - unique ID for this message
            # Visual: Artemis Console → Headers section > "userID"
            # Logical Type: Standard AMQP (but shows in Headers section)
            msg.id = f"msg-{self.message_count}"

            # User identifier - who created/sent this message
            # Visual: Artemis Console → Headers section > "userID"
            # Logical Type: Standard AMQP (but shows in Headers section)
            msg.user_id = "admin"

            # Subject - topic/title of the message
            # Visual: Artemis Console → Properties section > "properties.subject"
            # Logical Type: Standard AMQP Message Properties
            msg.subject = f"Extended Metadata Demo #{self.message_count}"

            # Reply-to address - where replies should be sent
            # Visual: Artemis Console → Properties section > "properties.replyTo"
            # Logical Type: Standard AMQP Message Properties
            msg.reply_to = "reply-queue"

            # Correlation ID - links related messages (request/reply pattern)
            # Visual: Artemis Console → Properties section > "properties.correlationId"
            # Logical Type: Standard AMQP Message Properties
            msg.correlation_id = f"corr-{self.message_count}"

            # Content type - what type of body content this is
            # Visual: Artemis Console → Properties section (may not be visible by default)
            # Logical Type: Standard AMQP Message Properties
            msg.content_type = "text/plain"

            # Content encoding - how the body is encoded
            # Visual: Artemis Console → Properties section (may not be visible by default)
            # Logical Type: Standard AMQP Message Properties
            msg.content_encoding = "utf-8"

            # ========================================
            # AMQP HEADERS (Broker Metadata)
            # Visual Section: Headers
            # Logical Type: Broker-controlled metadata
            # These control message behavior at the broker level
            # ========================================

            # Priority - message priority level (0-9, higher = more important)
            # Visual: Artemis Console → Headers section > "priority"
            # Logical Type: Broker Metadata
            msg.priority = 5

            # TTL (Time-To-Live) - how long message lives in milliseconds
            # Visual: Artemis Console → Headers section > "expiration" (calculated from TTL)
            # Logical Type: Broker Metadata
            msg.ttl = 300000  # 5 minutes

            # Timestamp - when message was created
            # Visual: Artemis Console → Headers section > "timestamp"
            # Logical Type: Broker Metadata
            msg.timestamp = int(time.time() * 1000)  # milliseconds

            # ========================================
            # CUSTOM APPLICATION PROPERTIES
            # Visual Section: Properties
            # Logical Type: Custom Application Properties (applicationProperties.*)
            # These are application-specific headers you define
            # ========================================

            if not msg.properties:
                msg.properties = {}

            # Custom user header
            # Visual: Artemis Console → Properties section > "applicationProperties.commander"
            # Logical Type: Custom Application Properties
            msg.properties["commander"] = "Thomas"

            # Business logic headers
            # Visual: Artemis Console → Properties section > "applicationProperties.order_id"
            # Logical Type: Custom Application Properties
            msg.properties["order_id"] = f"ORD-{self.message_count:05d}"
            msg.properties["customer_id"] = "CUST-12345"
            msg.properties["amount"] = "99.99"
            msg.properties["currency"] = "USD"

            # Operational headers
            # Visual: Artemis Console → Properties section > "applicationProperties.source_system"
            # Logical Type: Custom Application Properties
            msg.properties["source_system"] = "python-publisher"
            msg.properties["version"] = "1.0"
            msg.properties["environment"] = "learning"

            # Tracing/debugging headers
            # Visual: Artemis Console → Properties section > "applicationProperties.trace_id"
            # Logical Type: Custom Application Properties
            msg.properties["trace_id"] = f"trace-{self.message_count}"
            msg.properties["timestamp"] = str(time.time())
            msg.properties["retry_count"] = "0"

            # ========================================
            # SEND THE MESSAGE
            # ========================================

            self.sender.send(msg)

            # ========================================
            # DISPLAY WHAT WAS SENT
            # ========================================

            print(f"\n{'='*70}")
            print(f"[✓] Sent message #{self.message_count}")
            print(f"{'='*70}")

            print(f"\nBODY:")
            print(f"  {body}")

            print(f"\nAMQP MESSAGE PROPERTIES")
            print(f"Visual Section: Properties | Logical Type: Standard AMQP (properties.*)")
            print(f"  ID: {msg.id}")
            print(f"  User ID: {msg.user_id}")
            print(f"  Subject: {msg.subject}")
            print(f"  Reply-to: {msg.reply_to}")
            print(f"  Correlation ID: {msg.correlation_id}")
            print(f"  Content Type: {msg.content_type}")
            print(f"  Content Encoding: {msg.content_encoding}")

            print(f"\nAMQP HEADERS (Broker Metadata)")
            print(f"Visual Section: Headers | Logical Type: Broker-controlled Metadata")
            print(f"  Priority: {msg.priority}")
            print(f"  TTL: {msg.ttl} ms")
            print(f"  Timestamp: {msg.timestamp}")

            print(f"\nCUSTOM APPLICATION PROPERTIES")
            print(f"Visual Section: Properties | Logical Type: Custom (applicationProperties.*)")
            for key, value in msg.properties.items():
                print(f"  {key}: {value}")

            print(f"{'='*70}\n")

            self.last_send_time = time.time()

    def on_timer_task(self, event):
        """Called by timer to check if we should send another message"""
        # Check if 5 seconds have passed since last send
        if time.time() - self.last_send_time >= 5:
            self.send_message_extended()

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
        handler = PublisherExtended(broker, address)
        container = Container(handler)

        print(f"[...] Starting extended publisher (sending to {address})...\n")
        print("This script demonstrates ALL types of AMQP metadata and where they appear in Artemis:\n")
        print("ARTEMIS CONSOLE HAS 2 VISUAL SECTIONS:")
        print("  1. Headers         → Broker-controlled metadata (priority, ttl, timestamp, etc.)")
        print("  2. Properties      → Contains 3 logical types:\n")
        print("LOGICAL TYPES (within Properties section):")
        print("  a) Standard AMQP Message Properties (properties.*)  → subject, correlationId, replyTo, etc.")
        print("  b) Custom Application Properties (applicationProperties.*)  → your custom headers")
        print("  c) Broker-Added Properties (extraProperties._AMQ_*)  → Artemis-specific metadata")
        print("\n" + "="*70 + "\n")

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
