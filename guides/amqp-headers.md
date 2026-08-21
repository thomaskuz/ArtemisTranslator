# AMQP 1.0 Headers Guide

Understanding AMQP message headers and how to use them in Proton.

## Table of Contents

1. [What are Headers?](#what-are-headers)
2. [Types of Headers](#types-of-headers)
3. [Sending Headers](#sending-headers)
4. [Reading Headers](#reading-headers)
5. [Common Use Cases](#common-use-cases)
6. [Examples](#examples)

---

## What are Headers?

**Headers** are metadata attached to messages. They provide information **about** the message, not the message content itself.

Think of it like an envelope:
```
┌────────────────────────────┐
│ ENVELOPE (Headers)         │
├────────────────────────────┤
│ From: Alice                │
│ To: Bob                    │
│ Subject: Meeting           │
│ Date: 2024-08-17           │
├────────────────────────────┤
│ LETTER (Body)              │
│                            │
│ Hi Bob,                    │
│ Let's meet tomorrow.       │
│                            │
└────────────────────────────┘
```

- **Envelope = Headers** (metadata)
- **Letter = Body** (actual content)

## Types of Headers

### 1. Standard AMQP Message Properties

These are built-in AMQP 1.0 properties available on every message:

```python
msg.id                  # Unique message identifier
msg.subject             # Subject/topic of the message
msg.correlation_id      # Links related messages
msg.reply_to            # Where to send replies
msg.content_type        # Type of body (e.g., "application/json")
msg.content_encoding    # Encoding (e.g., "utf-8")
msg.timestamp           # When message was created
msg.ttl                 # Time-to-live in milliseconds
msg.priority            # Priority (0-9, higher = more important)
msg.user_id             # User who created the message
msg.group_id            # Message group identifier
```

### 2. Custom Application Properties

You can add your own headers for application-specific data:

```python
msg.properties["custom_header_1"] = "value"
msg.properties["order_id"] = "ORD-12345"
msg.properties["customer_id"] = "CUST-789"
```

### 3. Delivery Annotations (Broker-Specific)

Set by the message broker (like Artemis). Read-only from your code:

```python
msg.annotations  # Dictionary of broker-specific annotations
```

---

## Sending Headers

### Setting Standard AMQP Properties

```python
from proton import Message

msg = Message(body="Hello World")

# Set standard AMQP headers
msg.id = "msg-001"
msg.subject = "Greeting"
msg.reply_to = "reply-queue"
msg.correlation_id = "corr-123"
msg.content_type = "text/plain"
msg.priority = 5
msg.ttl = 60000  # 60 seconds in milliseconds
```

### Setting Custom Application Properties

```python
from proton import Message, PropertySet

msg = Message(body="Hello World")

# Initialize properties container if needed
if not msg.properties:
    msg.properties = PropertySet()

# Add custom headers
msg.properties["order_id"] = "ORD-12345"
msg.properties["customer_name"] = "John Doe"
msg.properties["amount"] = 99.99
msg.properties["timestamp"] = "2024-08-17T10:30:00Z"
```

### Complete Example

```python
def send_message_with_headers(self):
    """Send message with both standard and custom headers"""
    
    body = "Payment received"
    msg = Message(body=body)
    
    # Standard AMQP headers
    msg.id = "payment-001"
    msg.subject = "Payment Confirmation"
    msg.reply_to = "confirmations-queue"
    msg.correlation_id = "order-12345"
    msg.priority = 9  # High priority
    
    # Custom application headers
    if not msg.properties:
        from proton import PropertySet
        msg.properties = PropertySet()
    
    msg.properties["payment_method"] = "credit_card"
    msg.properties["amount"] = "99.99"
    msg.properties["currency"] = "USD"
    msg.properties["customer_id"] = "CUST-789"
    
    # Send
    self.sender.send(msg)
    print(f"[✓] Sent message with headers")
```

---

## Reading Headers

### Accessing Standard AMQP Properties

```python
def on_message(self, event):
    msg = event.message
    
    # Read standard headers
    print(f"Message ID: {msg.id}")
    print(f"Subject: {msg.subject}")
    print(f"Reply-to: {msg.reply_to}")
    print(f"Correlation ID: {msg.correlation_id}")
    print(f"Priority: {msg.priority}")
    print(f"Body: {msg.body}")
```

### Accessing Custom Application Properties

```python
def on_message(self, event):
    msg = event.message
    
    # Read custom headers
    if msg.properties:
        for key, value in msg.properties.items():
            print(f"Custom header '{key}': {value}")
    else:
        print("No custom headers")
```

### Safe Access (Handling Missing Headers)

```python
def on_message(self, event):
    msg = event.message
    
    # Safe access to standard headers
    message_id = msg.id or "no-id"
    subject = msg.subject or "no-subject"
    priority = msg.priority or 0
    
    # Safe access to custom headers
    if msg.properties:
        order_id = msg.properties.get("order_id", "unknown")
        customer = msg.properties.get("customer_name", "anonymous")
    else:
        order_id = "unknown"
        customer = "anonymous"
    
    print(f"Order ID: {order_id}, Customer: {customer}")
```

---

## Common Use Cases

### 1. Routing Messages

Use headers to route messages to different handlers:

```python
# Sender
msg.properties["message_type"] = "order"
msg.properties["destination"] = "warehouse-1"

# Receiver
message_type = msg.properties.get("message_type")
if message_type == "order":
    process_order(msg)
elif message_type == "invoice":
    process_invoice(msg)
```

### 2. Correlating Requests and Replies

Link a reply to its original request:

```python
# Original request
request_msg = Message(body="Get product details")
request_msg.id = "req-123"
request_msg.reply_to = "replies-queue"
sender.send(request_msg)

# Reply to that request
reply_msg = Message(body="Product details here...")
reply_msg.correlation_id = "req-123"  # Link to original
reply_msg.reply_to = "original-requester"  # Where to send it back
sender.send(reply_msg)
```

### 3. Priority-Based Processing

Different priorities for urgent vs. normal messages:

```python
# Urgent message
urgent_msg = Message(body="Critical alert!")
urgent_msg.priority = 9  # Highest priority
sender.send(urgent_msg)

# Normal message
normal_msg = Message(body="Regular update")
normal_msg.priority = 5  # Normal priority
sender.send(normal_msg)
```

### 4. Message Expiration

Messages that expire after a certain time:

```python
msg = Message(body="Time-sensitive offer")
msg.ttl = 300000  # Expires after 5 minutes (300000 ms)
sender.send(msg)
```

### 5. Tracing and Debugging

Add debugging information to headers:

```python
import uuid
import time

msg = Message(body="Processing request")

# Add tracing headers
msg.properties["trace_id"] = str(uuid.uuid4())
msg.properties["timestamp"] = str(time.time())
msg.properties["source_system"] = "order-service"
msg.properties["version"] = "1.0"

sender.send(msg)
```

---

## Examples

### Example 1: Order Processing

```python
# Publisher sending order
from proton import Message

def send_order(self, order_id, items, customer):
    body = f"Order with {len(items)} items"
    msg = Message(body=body)
    
    # Standard headers
    msg.id = f"order-{order_id}"
    msg.subject = "New Order"
    msg.priority = 8  # Important
    msg.reply_to = "order-confirmations"
    
    # Custom headers
    msg.properties["order_id"] = order_id
    msg.properties["customer_id"] = customer["id"]
    msg.properties["customer_name"] = customer["name"]
    msg.properties["total_items"] = str(len(items))
    msg.properties["timestamp"] = str(time.time())
    
    self.sender.send(msg)

# Consumer receiving order
def on_message(self, event):
    msg = event.message
    
    order_id = msg.properties.get("order_id")
    customer = msg.properties.get("customer_name")
    total = msg.properties.get("total_items")
    
    print(f"Order {order_id} from {customer} ({total} items)")
    
    # Process the order
    process_order(order_id, customer)
```

### Example 2: Request/Reply Pattern

```python
# Publisher sends request
def send_request(self):
    msg = Message(body="What is the stock level?")
    msg.id = "req-stock-001"
    msg.subject = "Stock Query"
    msg.reply_to = "response-queue"
    msg.correlation_id = "req-stock-001"  # Track this request
    msg.properties["product_id"] = "PROD-123"
    
    self.sender.send(msg)

# Consumer replies
def on_message(self, event):
    msg = event.message
    
    # Read the correlation ID to know what request this is for
    correlation_id = msg.correlation_id
    
    # Get the reply-to address
    reply_to = msg.reply_to
    
    # Process and send reply
    stock_level = get_stock(msg.properties["product_id"])
    
    reply = Message(body=f"Stock level: {stock_level}")
    reply.correlation_id = correlation_id  # Link back
    
    # Send to reply-to address (in production, would send to that queue)
```

### Example 3: Error Handling with Headers

```python
# Publisher sends with tracing
def send_payment(self, transaction_id, amount):
    msg = Message(body=f"Process payment: ${amount}")
    
    msg.id = f"payment-{transaction_id}"
    msg.subject = "Payment Processing"
    msg.properties["transaction_id"] = transaction_id
    msg.properties["amount"] = str(amount)
    msg.properties["retry_count"] = "0"
    msg.properties["max_retries"] = "3"
    
    self.sender.send(msg)

# Consumer handles errors
def on_message(self, event):
    msg = event.message
    
    try:
        process_payment(msg.properties["amount"])
        print(f"[✓] Payment {msg.properties['transaction_id']} succeeded")
    except Exception as e:
        # Handle retry
        retry_count = int(msg.properties.get("retry_count", 0))
        max_retries = int(msg.properties.get("max_retries", 3))
        
        if retry_count < max_retries:
            # Send for retry
            msg.properties["retry_count"] = str(retry_count + 1)
            self.sender.send(msg)
            print(f"[!] Retry #{retry_count + 1}")
        else:
            # Send to dead-letter queue
            print(f"[✗] Failed after {max_retries} retries")
```

---

## Testing Headers

Use the provided scripts to test:

**Terminal 1: Consumer**
```bash
python consumer_with_headers_amqp.py
```

**Terminal 2: Publisher**
```bash
python publisher_with_headers_amqp.py
```

The consumer will display all headers received from the publisher!

---

## Summary

| Type | Purpose | Example |
|------|---------|---------|
| **Standard AMQP** | Built-in metadata | `msg.id`, `msg.priority`, `msg.ttl` |
| **Custom Properties** | Application-specific | `msg.properties["order_id"]` |
| **Delivery Annotations** | Broker-added metadata | Read from `msg.annotations` |

Use headers to:
- ✅ Route messages to correct handlers
- ✅ Correlate requests and replies
- ✅ Set message priority
- ✅ Add tracing/debugging info
- ✅ Track retries and errors
- ✅ Add business logic metadata
