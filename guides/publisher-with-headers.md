# Publisher with Headers Guide

Learn how to send AMQP messages with custom headers and metadata.

## Overview

The `publisher_with_headers.py` script sends messages to Artemis every 5 seconds with both **standard AMQP message properties** and **custom application headers**.

## Running the Script

```bash
python publisher_with_headers.py
```

Output:
```
[...] Starting publisher with headers (sending to test.queue)...
[✓] Connected to Artemis
[✓] Sender ready for queue: test.queue
[!] Sending messages with headers every 5 seconds (Ctrl+C to stop)

[✓] Sent message #1: Hello from Artemis (#1)
    ID: msg-1
    Subject: Test Subject
    Correlation ID: corr-1
    Reply-to: reply-queue
    Custom headers: {'commander': 'Thomas', 'custom_header_1': 'custom_value_1', ...}

[✓] Sent message #2: Hello from Artemis (#2)
    ...
```

## Message Structure

Each message contains:

### Standard AMQP Message Properties

```python
msg.id = "msg-1"                    # Unique message identifier
msg.subject = "Test Subject"        # Message topic/title
msg.reply_to = "reply-queue"        # Where replies should go
msg.correlation_id = "corr-1"       # Links related messages
```

### Custom Application Headers

```python
msg.properties["commander"] = "Thomas"           # Custom header
msg.properties["custom_header_1"] = "value"      # Custom header
msg.properties["custom_header_2"] = "data"       # Custom header
msg.properties["timestamp"] = "1728..." # Custom header
```

## Where Headers Appear in Artemis

See [headers-structure.md](headers-structure.md) for detailed explanation of:
- Visual sections (Headers vs Properties)
- Logical types (Standard AMQP, Custom Application, Broker-Added)
- Exact paths in Artemis console

## Script Architecture

### Constructor (`__init__`)
```python
def __init__(self, url, queue):
    self.url = url                    # Broker URL with auth
    self.queue = queue                # Target queue
    self.sender = None                # Will be set when connection opens
    self.message_count = 0            # Track message sequence
    self.last_send_time = 0           # Track 5-second interval
    self.reactor = None               # Event loop manager
```

### Connection Flow

1. **on_start()** → Initiates connection to Artemis
2. **on_connection_opened()** → Creates sender link
3. **on_link_opened()** → Sender ready, starts timer
4. **on_timer_task()** → Called every 1 second to check if 5 seconds passed
5. **send_message_with_headers()** → Sends message with all headers

### Timer Mechanism

The script uses a recursive timer:
```python
def on_link_opened(self, event):
    self.send_message_with_headers()
    if self.reactor:
        self.reactor.schedule(1.0, self)  # Schedule next check in 1 second

def on_timer_task(self, event):
    if time.time() - self.last_send_time >= 5:
        self.send_message_with_headers()
    
    if self.reactor:
        self.reactor.schedule(1.0, self)  # Reschedule next check
```

This creates a self-repeating timer that:
- Fires every 1 second
- Checks if 5 seconds have passed since last send
- Sends a message if yes
- Reschedules itself

## Customizing Messages

### Change Interval

```python
# In on_timer_task(), change the condition:
if time.time() - self.last_send_time >= 10:  # 10 seconds instead of 5
    self.send_message_with_headers()

# And in schedule calls:
self.reactor.schedule(2.0, self)  # Check every 2 seconds instead of 1
```

### Add Custom Headers

```python
def send_message_with_headers(self):
    # ... existing code ...
    
    # Add your custom headers
    msg.properties["your_key"] = "your_value"
    msg.properties["order_id"] = "ORD-123"
    msg.properties["user_name"] = "Alice"
```

### Change Message Content

```python
def send_message_with_headers(self):
    # Change the body
    body = f"Custom message #{self.message_count}: Your content here"
    
    # Or change any standard property
    msg.subject = "Your Subject"
    msg.correlation_id = f"your-prefix-{self.message_count}"
```

## Testing with Consumer

**Terminal 1: Consumer**
```bash
python consumer_with_headers.py
```

**Terminal 2: Publisher**
```bash
python publisher_with_headers.py
```

The consumer displays all headers from each message!

## Viewing in Artemis Console

1. Go to http://localhost:8161
2. Navigate to **Queues** → **test.queue**
3. Click on a message to see all headers and properties
4. Look for:
   - **Headers section**: priority, timestamp, userID, protocol, etc.
   - **Properties section**: properties.* (standard AMQP) and applicationProperties.* (custom)

## Key Concepts

### Message Lifecycle

```
send_message_with_headers()
    ↓
1. Create Message with body
    ↓
2. Add standard AMQP properties (id, subject, reply_to, etc.)
    ↓
3. Add custom application headers (msg.properties)
    ↓
4. Send to queue via sender
    ↓
Message stored in Artemis
    ↓
Consumer receives and parses
```

### Acknowledgment

The publisher doesn't require message acknowledgment — it just sends. The consumer is responsible for acknowledging (in `consumer_with_headers.py`).

### Timer Accuracy

The timer checks every 1 second but sends every 5 seconds:
- More frequent checks (every 1s) = more accurate interval
- Less frequent checks = more efficient but less precise

Change both values if needed, but checking more frequently than sending makes sense.

## Next Steps

1. Run publisher and consumer together to see headers in action
2. View messages in Artemis console to see where headers appear
3. Customize headers for your use case
4. Read [headers-structure.md](headers-structure.md) to understand the visual vs logical structure
5. Try [publisher_with_headers_extended.py](../publisher_with_headers_extended.py) for all metadata types
