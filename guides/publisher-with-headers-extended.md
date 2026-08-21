# Publisher with Headers Extended Guide

Comprehensive guide to ALL AMQP metadata types with detailed comments showing exactly where each appears in Artemis.

## Overview

The `publisher_with_headers_extended_amqp.py` script demonstrates **all types of AMQP message metadata** with extensive comments explaining:
- Visual sections in Artemis console (Headers vs Properties)
- Logical types within each section
- Exact paths where each property appears

This is an **educational version** designed to teach you the complete AMQP message structure.

## Running the Script

```bash
python publisher_with_headers_extended_amqp.py
```

Output shows:
```
[...] Starting extended publisher (sending to test.queue)...

This script demonstrates ALL types of AMQP metadata and where they appear in Artemis:

ARTEMIS CONSOLE HAS 2 VISUAL SECTIONS:
  1. Headers         → Broker-controlled metadata
  2. Properties      → Contains 3 logical types

LOGICAL TYPES (within Properties section):
  a) Standard AMQP Message Properties (properties.*)
  b) Custom Application Properties (applicationProperties.*)
  c) Broker-Added Properties (extraProperties._AMQ_*)

======================================================================

[✓] Sent message #1

BODY:
  Extended message #1 with all metadata types

AMQP MESSAGE PROPERTIES
Visual Section: Properties | Logical Type: Standard AMQP (properties.*)
  ID: msg-1
  User ID: admin
  Subject: Extended Metadata Demo #1
  Reply-to: reply-queue
  Correlation ID: corr-1
  Content Type: text/plain
  Content Encoding: utf-8

AMQP HEADERS (Broker Metadata)
Visual Section: Headers | Logical Type: Broker-controlled Metadata
  Priority: 5
  TTL: 300000 ms
  Timestamp: 1728...

CUSTOM APPLICATION PROPERTIES
Visual Section: Properties | Logical Type: Custom (applicationProperties.*)
  commander: Thomas
  order_id: ORD-00001
  customer_id: CUST-12345
  ...
```

## The Two-Level Structure

### VISUAL SECTIONS (What you see in Artemis Console)

**1. Headers Section**
- Broker-controlled metadata
- Properties you can partially control (priority, ttl, timestamp)
- Broker-determined values (protocol, durable, expiration)

**2. Properties Section**
- Contains 3 logical types of data
- Everything that isn't in Headers

### LOGICAL TYPES (Data categories)

**Within the Properties section, there are 3 types:**

#### Type A: Standard AMQP Message Properties (`properties.*`)
These are built-in AMQP 1.0 properties:
```python
msg.id                 # Message ID
msg.user_id            # Who sent it
msg.subject            # Topic/title
msg.reply_to           # Reply destination
msg.correlation_id     # Links related messages
msg.content_type       # Body type (application/json, text/plain, etc.)
msg.content_encoding   # Encoding (utf-8, etc.)
```

Shows in Artemis as:
```
Properties
├── properties.subject
├── properties.correlationId
├── properties.replyTo
└── ...
```

#### Type B: Custom Application Properties (`applicationProperties.*`)
These are your own custom headers:
```python
msg.properties["commander"] = "Thomas"
msg.properties["order_id"] = "ORD-001"
msg.properties["trace_id"] = "trace-123"
msg.properties["custom_key"] = "custom_value"
```

Shows in Artemis as:
```
Properties
├── applicationProperties.commander
├── applicationProperties.order_id
├── applicationProperties.trace_id
└── applicationProperties.custom_key
```

#### Type C: Broker-Added Properties (`extraProperties._AMQ_*`)
Set by Artemis automatically:
```
Properties
└── extraProperties._AMQ_AD  (Artemis internal)
```

You cannot set these — they're read-only.

## Message Structure in Code

### Step 1: Create Message

```python
body = f"Extended message #{self.message_count} with all metadata types"
msg = Message(body=body)
```

### Step 2: Add Standard AMQP Properties

```python
# Visual: Properties section
# Logical Type: Standard AMQP Message Properties

msg.id = f"msg-{self.message_count}"
msg.user_id = "admin"
msg.subject = f"Extended Metadata Demo #{self.message_count}"
msg.reply_to = "reply-queue"
msg.correlation_id = f"corr-{self.message_count}"
msg.content_type = "text/plain"
msg.content_encoding = "utf-8"
```

### Step 3: Add Headers (Broker Metadata)

```python
# Visual: Headers section
# Logical Type: Broker-controlled Metadata

msg.priority = 5
msg.ttl = 300000  # 5 minutes in milliseconds
msg.timestamp = int(time.time() * 1000)
```

### Step 4: Add Custom Application Properties

```python
# Visual: Properties section
# Logical Type: Custom Application Properties

if not msg.properties:
    msg.properties = {}

msg.properties["commander"] = "Thomas"
msg.properties["order_id"] = f"ORD-{self.message_count:05d}"
msg.properties["customer_id"] = "CUST-12345"
msg.properties["trace_id"] = f"trace-{self.message_count}"
```

### Step 5: Send

```python
self.sender.send(msg)
```

## Viewing in Artemis Console

1. Go to http://localhost:8161
2. Navigate to **Queues** → **test.queue**
3. Click on any message
4. You'll see all metadata organized into sections

**Headers Section:**
```
address: test.queue
durable: false
expiration: never (calculated from TTL)
largeMessage: false
messageID: 1
persistentSize: 216 Bytes
priority: 5           ← You set this
protocol: AMQP
redelivered: false
timestamp: 1728...    ← You set this
type: 3 (text)
userID: ID:msg-1      ← You set this
```

**Properties Section:**
```
properties.subject: Extended Metadata Demo #1
properties.correlationId: corr-1
properties.replyTo: reply-queue

applicationProperties.commander: Thomas
applicationProperties.order_id: ORD-00001
applicationProperties.customer_id: CUST-12345
applicationProperties.trace_id: trace-1

extraProperties._AMQ_AD: test.queue  ← Broker-added
```

## Key Learnings

### You Control These (in Headers section)

```python
msg.priority = 5      # ✅ Control priority
msg.ttl = 300000      # ✅ Control time-to-live
msg.timestamp = time  # ✅ Control timestamp
msg.user_id = "admin" # ✅ Control user ID
```

### Broker Controls These (in Headers section)

```
durable             ← Set by queue configuration
messageID           ← Generated by broker
address             ← Determined by queue
protocol            ← Set by broker
expiration          ← Calculated from TTL
```

### You Control These (in Properties section)

```python
# Standard AMQP
msg.subject = "title"
msg.correlation_id = "123"
msg.reply_to = "queue"

# Custom Application
msg.properties["my_key"] = "my_value"
```

## Real-World Example: Order Processing

```python
def send_order_message(self):
    msg = Message(body="Process order")
    
    # Standard properties for routing/correlation
    msg.id = f"order-{order_id}"
    msg.subject = "Order Processing"
    msg.correlation_id = f"order-{order_id}"
    msg.reply_to = "order-confirmations"
    
    # Headers for priority handling
    msg.priority = 9  # High priority order
    msg.ttl = 3600000  # 1 hour
    
    # Custom properties for business logic
    msg.properties["commander"] = "Thomas"
    msg.properties["order_id"] = order_id
    msg.properties["customer_id"] = customer_id
    msg.properties["amount"] = amount
    msg.properties["priority_level"] = "high"
    
    self.sender.send(msg)
```

## Testing

**Terminal 1:**
```bash
python consumer_with_headers_amqp.py
```

**Terminal 2:**
```bash
python publisher_with_headers_extended_amqp.py
```

Watch both terminal output and Artemis console to see how metadata flows through the system!

## Next Steps

1. Run this script and observe all metadata types
2. Check Artemis console to see where each appears
3. Read [headers-structure.md](headers-structure.md) for complete visual/logical breakdown
4. Modify the script to add your own custom headers
5. Build real-world flows using this pattern
