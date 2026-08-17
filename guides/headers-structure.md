# AMQP Headers Structure Guide

Understanding the visual sections vs logical types in Artemis message headers.

## The Confusion: Visual vs Logical

AMQP messages have a complex structure that appears differently in Artemis console than the logical organization in the AMQP 1.0 specification.

## Visual Sections (What You See in Artemis)

When you view a message in Artemis console, you see **2 main sections**:

### Section 1: Headers

**What it contains:**
- Broker-level metadata
- Transport-related properties
- Properties that control message behavior

**Examples:**
```
address          → test.queue
durable          → false
expiration       → never
largeMessage     → false
messageID        → 49
persistentSize   → 216 Bytes
priority         → 4
protocol         → AMQP
redelivered      → false
timestamp        → (value)
type             → 3 (text)
userID           → ID:msg-1
```

### Section 2: Properties

**What it contains:**
- Standard AMQP message properties
- Custom application headers
- Broker-added metadata

**Organized as:**
```
properties.*                    → Standard AMQP
applicationProperties.*         → Custom headers
extraProperties._AMQ_*         → Broker-added
```

---

## Logical Types (The Real Organization)

AMQP 1.0 defines **3 logical categories** of message metadata. These don't neatly map to visual sections!

### Logical Type 1: AMQP Message Properties

**What they are:**
Standard AMQP 1.0 properties defined in the specification.

**Examples:**
```
message-id          → Unique identifier
user-id             → Who created it
subject             → Message title/topic
reply-to            → Reply destination
correlation-id      → Links related messages
content-type        → Body format (application/json, text/plain)
content-encoding    → Body encoding (utf-8)
```

**Where they appear in Artemis:**
- Some show in **Headers section** (userID, messageID)
- Most show in **Properties section** as `properties.*`

**In Python (Proton):**
```python
msg.id = "msg-1"
msg.user_id = "admin"
msg.subject = "Title"
msg.reply_to = "queue"
msg.correlation_id = "corr-1"
msg.content_type = "application/json"
msg.content_encoding = "utf-8"
```

### Logical Type 2: Message Annotations

**What they are:**
Broker-to-broker metadata, not typically visible to applications.

**Where they appear:**
Usually not visible in consumer view (internal broker use).

### Logical Type 3: Application Properties

**What they are:**
Custom headers you define for your application.

**Examples:**
```
commander           → Your custom header
order_id            → Business data
customer_id         → Business data
trace_id            → Tracing/debugging
retry_count         → Operational tracking
```

**Where they appear in Artemis:**
**Properties section** as `applicationProperties.*`

**In Python (Proton):**
```python
msg.properties["commander"] = "Thomas"
msg.properties["order_id"] = "ORD-001"
msg.properties["trace_id"] = "trace-123"
```

---

## The Mapping (Visual → Logical)

Here's how the visual sections map to logical types:

```
ARTEMIS CONSOLE                 LOGICAL TYPE
═══════════════════════════════════════════════════════════

Headers Section
├── address                     → Broker metadata
├── durable                     → Broker metadata
├── protocol                    → Broker metadata
├── priority        ✅ You set  → AMQP Message Property (Header)
├── ttl/expiration  ✅ You set  → AMQP Message Property (Header)
├── timestamp       ✅ You set  → AMQP Message Property (Header)
├── userID          ✅ You set  → AMQP Message Property
└── ... (others)                → Broker metadata

Properties Section
├── properties.*                → AMQP Message Properties
│   ├── subject                 ✅ You set
│   ├── correlationId           ✅ You set
│   ├── replyTo                 ✅ You set
│   ├── contentType             ✅ You set
│   └── ...
│
├── applicationProperties.*     → Custom Application Properties
│   ├── commander              ✅ You set
│   ├── order_id               ✅ You set
│   ├── trace_id               ✅ You set
│   └── ... (your custom keys)
│
└── extraProperties._AMQ_*     → Broker-Added (Read-only)
    └── ... (Artemis internals)
```

---

## What You Can Control

### In Headers Section (Broker Metadata)

```python
# ✅ CAN SET
msg.priority = 5              # 0-9, higher = more important
msg.ttl = 300000              # milliseconds
msg.timestamp = time.time()   # when created
msg.user_id = "admin"         # who sent it

# ❌ CANNOT SET (Broker controls)
# durable, address, protocol, expiration, messageID, redelivered
```

### In Properties Section (AMQP Message Properties)

```python
# ✅ CAN SET
msg.id = "msg-1"
msg.subject = "Title"
msg.reply_to = "queue"
msg.correlation_id = "corr-1"
msg.content_type = "application/json"
msg.content_encoding = "utf-8"
```

### In Properties Section (Custom Application)

```python
# ✅ CAN SET (Unlimited)
msg.properties["any_key"] = "any_value"
msg.properties["commander"] = "Thomas"
msg.properties["order_id"] = "ORD-001"
```

---

## Real-World Example: Order Message

```python
# Create message
msg = Message(body="Process order")

# AMQP HEADERS (control message behavior)
msg.priority = 9              # High priority
msg.ttl = 3600000             # 1 hour timeout

# AMQP MESSAGE PROPERTIES (standard routing/metadata)
msg.id = f"order-{order_id}"
msg.subject = "Order Processing"
msg.reply_to = "order-responses"
msg.correlation_id = f"order-{order_id}"

# CUSTOM APPLICATION PROPERTIES (your business data)
msg.properties["commander"] = "Thomas"
msg.properties["order_id"] = order_id
msg.properties["customer_id"] = customer_id
msg.properties["amount"] = amount
msg.properties["order_priority"] = "expedited"

# Send
self.sender.send(msg)
```

**In Artemis console, this appears as:**

```
Headers Section:
- priority: 9
- ttl/expiration: 1 hour
- userID: (default from connection)
- ... (other broker metadata)

Properties Section:
- properties.subject: Order Processing
- properties.correlationId: order-12345
- properties.replyTo: order-responses

- applicationProperties.commander: Thomas
- applicationProperties.order_id: ORD-12345
- applicationProperties.customer_id: CUST-001
- applicationProperties.amount: 199.99
- applicationProperties.order_priority: expedited
```

---

## Common Misconceptions

### "I can add custom headers to the Headers section"
❌ **False.** Headers section is for broker metadata only. Custom data goes to **applicationProperties** in Properties section.

### "AMQP Message Properties all go to Properties section"
❌ **Partially false.** Some like `id` and `user_id` show in Headers section, most show in Properties section. It's confusing!

### "I can set the expiration directly"
❌ **False.** Expiration is calculated from TTL by the broker. You set TTL, broker calculates expiration.

### "applicationProperties are the same as AMQP properties"
❌ **False.** They're different logical types within the same visual Properties section.

---

## Best Practices

1. **Use AMQP Message Properties for routing/correlation**
   ```python
   msg.subject = "OrderProcessing"        # What is it?
   msg.correlation_id = "order-123"       # Link to request
   msg.reply_to = "order-responses"       # Where to reply
   ```

2. **Use Application Properties for business data**
   ```python
   msg.properties["customer_id"] = cust_id
   msg.properties["order_amount"] = amount
   msg.properties["priority"] = priority
   ```

3. **Use Headers for message behavior**
   ```python
   msg.priority = 9                       # How important?
   msg.ttl = 3600000                      # How long to keep?
   ```

4. **Be consistent**
   - Always include correlation_id for trackable messages
   - Always set subject to message type
   - Always use same custom property names

---

## Summary Table

| Category | Visual Section | Logical Type | You Control? | Examples |
|----------|---|---|---|---|
| Message behavior | Headers | AMQP Headers | ✅ Partial | priority, ttl, timestamp |
| Standard properties | Both | AMQP Properties | ✅ Yes | subject, correlation_id, reply_to |
| Custom data | Properties | App Properties | ✅ Yes | commander, order_id, trace_id |
| Broker metadata | Headers | Broker Meta | ❌ No | protocol, durable, address |
| Broker added | Properties | Broker Meta | ❌ No | extraProperties._AMQ_* |

---

## Further Learning

- See [publisher-with-headers.md](publisher-with-headers.md) for basic usage
- See [publisher-with-headers-extended.md](publisher-with-headers-extended.py) for all metadata types with detailed comments
- Run `publisher_with_headers_extended.py` and check Artemis console to see this structure in action
