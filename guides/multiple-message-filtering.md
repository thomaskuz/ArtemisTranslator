# Multiple Message Filtering with Multicast Routing

Complete guide for setting up one message source with multiple filtered queues to route messages to different destinations based on application properties.

## Architecture Overview

Instead of losing messages that don't match a filter, **multicast routing** delivers messages to ALL matching queues:

```
Publisher (Python)
    ↓ test.queue
Artemis
    ↓
NodeRed AMQP In
    ↓
Function Node (Transform)
    ↓
NodeRed AMQP Out
    ↓ transform.queue (Multicast Address)
Artemis
    ├─ Queue: all-messages (no filter)
    │  └─ Receives: ALL messages (Thomas + Alice + others)
    ├─ Queue: thomas-only (filter: commander = 'Thomas')
    │  └─ Receives: Only Thomas messages
    └─ Queue: alice-only (filter: commander = 'Alice')
       └─ Receives: Only Alice messages
```

## Key Concept: Multicast vs Anycast

| Aspect | Anycast | Multicast |
|--------|---------|-----------|
| **Routing** | Message → ONE queue | Message → ALL matching queues |
| **Use Case** | Load balancing | Fan-out, broadcast |
| **Filters** | Skip non-matching | Each queue gets own filter |
| **Messages** | Not duplicated | Delivered to all queues |

## Prerequisites

- ✅ Artemis running on port 5672
- ✅ NodeRed with @meowwolf AMQP node
- ✅ Python publisher script
- ✅ Understanding of AMQP filters and application properties

## Step 1: Clean Up Old Configuration

### Delete Old Filtered Queue

In Artemis Admin Console (**http://localhost:8161**):

1. Click **Queues** tab
2. Find `filtered-thomas-queue` (if it exists)
3. Click the three-dot menu (⋯)
4. Select **Delete**

### Delete Old Address (Optional)

1. Click **Addresses** tab
2. Find `filtered-thomas-queue` address
3. Click three-dot menu
4. Select **Delete**

## Step 2: Create Multicast Address

### Create the Address

1. Go to **http://localhost:8161**
2. Click **Addresses** tab
3. Click **Create Address**
4. Fill in:
   - **Name**: `transform.queue`
   - **Routing type**: `Multicast` ← **IMPORTANT**
5. Click **Create**

**Why Multicast?** So messages are delivered to ALL queues on this address (each evaluates its own filter).

## Step 3: Create Multiple Filtered Queues

All queues will be attached to the **same address** (`transform.queue`) but with different filters.

### Queue 1: All Messages (No Filter)

1. Click **Queues** tab
2. Click **Create Queue**
3. Fill in:
   - **Name**: `all-messages`
   - **Address**: `transform.queue`
   - **Filter**: (leave empty)
   - **Durable**: ✅ `true`
4. Click **Create**

**Purpose:** Receives ALL messages regardless of commander value. Use this as a backup/audit queue.

### Queue 2: Thomas Only

1. Click **Create Queue**
2. Fill in:
   - **Name**: `thomas-only`
   - **Address**: `transform.queue`
   - **Filter**: `commander = 'Thomas'`
   - **Durable**: ✅ `true`
3. Click **Create**

**Purpose:** Only messages with `commander = 'Thomas'` arrive here.

### Queue 3: Alice Only

1. Click **Create Queue**
2. Fill in:
   - **Name**: `alice-only`
   - **Address**: `transform.queue`
   - **Filter**: `commander = 'Alice'`
   - **Durable**: ✅ `true`
3. Click **Create**

**Purpose:** Only messages with `commander = 'Alice'` arrive here.

### Queue 4 (Optional): Other Users

For any other commanders:

1. Click **Create Queue**
2. Fill in:
   - **Name**: `other-users`
   - **Address**: `transform.queue`
   - **Filter**: `NOT (commander = 'Thomas' OR commander = 'Alice')`
   - **Durable**: ✅ `true`
3. Click **Create**

**Purpose:** Catches any messages that don't match Thomas or Alice.

## Step 4: Verify NodeRed Configuration

Your NodeRed AMQP Out node should already be configured correctly:

✅ **Address**: `transform.queue` (the multicast address)

**No changes needed!** The flow automatically broadcasts to all queues on this address.

## Step 5: Test with Alternating Publisher

### Run the Publisher

```bash
python simple_publisher_alternating_amqp.py
```

Output:
```
[✓] Sent message #1
    Commander: Thomas

[✓] Sent message #2
    Commander: Alice

[✓] Sent message #3
    Commander: Thomas
```

### Start NodeRed Flow

Click **Deploy** in NodeRed

### Monitor in Artemis Console

Go to **http://localhost:8161** → **Queues**

Watch the queue counts update as messages arrive:

```
all-messages     Queue Count: 6 (1, 2, 3, 4, 5, 6)
thomas-only      Queue Count: 3 (1, 3, 5)
alice-only       Queue Count: 3 (2, 4, 6)
other-users      Queue Count: 0
```

## Expected Message Distribution

### Complete Sequence

| Message | Commander | all-messages | thomas-only | alice-only | other-users |
|---------|-----------|--------------|-------------|-----------|-------------|
| #1 | Thomas | ✅ | ✅ | ❌ | ❌ |
| #2 | Alice | ✅ | ❌ | ✅ | ❌ |
| #3 | Thomas | ✅ | ✅ | ❌ | ❌ |
| #4 | Alice | ✅ | ❌ | ✅ | ❌ |
| #5 | Thomas | ✅ | ✅ | ❌ | ❌ |
| #6 | Alice | ✅ | ❌ | ✅ | ❌ |

### Summary
- **all-messages**: 6/6 (100%)
- **thomas-only**: 3/6 (50%)
- **alice-only**: 3/6 (50%)
- **other-users**: 0/6 (0%)

## Understanding the Flow

### 1. Message Arrives at Address

```
NodeRed sends: {"commander": "Alice", "message_number": 2}
    ↓
Address: transform.queue receives it
    ↓
Artemis checks: "Is there a queue here?"
    ↓
Answer: Yes! There are 4 queues
```

### 2. Evaluate Filters

```
Queue: all-messages (filter: empty)
  → Check: No filter defined?
  → Result: ACCEPT ✅

Queue: thomas-only (filter: commander = 'Thomas')
  → Check: Is commander = 'Alice'?
  → Result: REJECT ❌

Queue: alice-only (filter: commander = 'Alice')
  → Check: Is commander = 'Alice'?
  → Result: ACCEPT ✅

Queue: other-users (filter: NOT (commander = 'Thomas' OR commander = 'Alice'))
  → Check: Is commander neither Thomas nor Alice?
  → Result: REJECT ❌
```

### 3. Message Delivered

```
Message #2 is delivered to:
  - all-messages ✅
  - alice-only ✅
```

## Advanced: Adding More Commanders

To add a third commander (e.g., "Bob"):

### 1. Update Publisher Script

Edit `simple_publisher_alternating_amqp.py`:
```python
self.commanders = ["Thomas", "Alice", "Bob"]
```

### 2. Create Queue for Bob

In Artemis:
1. **Queues** → **Create Queue**
2. Fill in:
   - **Name**: `bob-only`
   - **Address**: `transform.queue`
   - **Filter**: `commander = 'Bob'`
   - **Durable**: ✅ `true`
3. **Create**

### 3. Update "other-users" Filter (Optional)

If you want to keep only Thomas and Alice:
```
NOT (commander = 'Thomas' OR commander = 'Alice')
```

Messages from Bob will go to `other-users` queue.

Or create specific queues for each commander instead of using "other-users".

## Filter Expression Examples

### Single Commander
```
commander = 'Thomas'
```

### Multiple Commanders (OR)
```
commander = 'Thomas' OR commander = 'Alice'
```

### Exclude Commanders (NOT)
```
NOT commander = 'Bob'
```

### Numeric Properties
```
message_number > 10
message_number >= 5 AND message_number <= 15
```

### Boolean Properties
```
transformed = true
```

### Combined Conditions
```
commander = 'Thomas' AND transformed = true AND message_number > 5
```

## Use Cases

### 1. User-Based Routing
```
alice-queue:   Filter: commander = 'Alice'
thomas-queue:  Filter: commander = 'Thomas'
bob-queue:     Filter: commander = 'Bob'
audit-queue:   Filter: (no filter - all messages)
```

### 2. Priority-Based Routing
```
high-priority:  Filter: priority >= 8
medium:         Filter: priority >= 5 AND priority < 8
low-priority:   Filter: priority < 5
all-messages:   Filter: (no filter)
```

### 3. Source-Based Routing
```
nodered-messages:  Filter: source = 'NodeRed'
python-messages:   Filter: source = 'Python'
other-sources:     Filter: NOT (source = 'NodeRed' OR source = 'Python')
```

### 4. Combination: Source + User
```
thomas-from-nodered:  Filter: commander = 'Thomas' AND source = 'NodeRed'
alice-from-python:    Filter: commander = 'Alice' AND source = 'Python'
all-messages:         Filter: (no filter)
```

## Troubleshooting

### Messages Only Arrive in all-messages

**Problem:** Filtered queues receive nothing, only all-messages has messages.

**Solutions:**
1. ✅ Check address routing type is **Multicast** (not Anycast)
2. ✅ Verify filter syntax: `commander = 'Thomas'` (with quotes)
3. ✅ Verify property names match exactly: `commander` not `cmd`
4. ✅ Check message actually has the property (use consumer to verify)

### Some Messages Missing Entirely

**Problem:** Total messages in all queues < expected count.

**Solutions:**
1. ✅ Verify no `other-users` filter is too restrictive
2. ✅ Check all queues are durable (not temporary)
3. ✅ Verify address is still Multicast
4. ✅ Restart Artemis if queues were edited mid-stream

### Filter Syntax Errors

**Problem:** Queue creation fails with "Invalid filter expression".

**Solutions:**
1. ✅ Use single quotes for strings: `'Thomas'` not `"Thomas"`
2. ✅ Property names are case-sensitive: `commander` not `Commander`
3. ✅ Use proper operators: `=` not `==`
4. ✅ For multi-word filters, use parentheses: `(commander = 'Thomas') AND (transformed = true)`

## Performance Considerations

### Message Duplication
- Multicast **duplicates** messages to each queue
- Storage: Each queue stores its own copy
- Network: Message sent once, but stored multiple times

### When to Use Multicast
- ✅ Multiple subscribers need same message
- ✅ Filtering at queue level is acceptable
- ✅ Message deduplication not needed

### When to Use Anycast
- ✅ Load balancing (distribute across queues)
- ✅ Only one consumer needed
- ✅ Minimize storage

## Complete Example: Three Commanders

### Setup
```
Publisher sends: Thomas, Alice, Bob (rotating every 5 seconds)
Address: transform.queue (Multicast)

Queues:
- all-messages        (no filter)
- thomas-only         (commander = 'Thomas')
- alice-only          (commander = 'Alice')
- bob-only            (commander = 'Bob')
```

### After 30 Seconds (6 messages)
```
Publisher sends:
  Message 1: Thomas
  Message 2: Alice
  Message 3: Bob
  Message 4: Thomas
  Message 5: Alice
  Message 6: Bob

Queue Distribution:
  all-messages: [1, 2, 3, 4, 5, 6]           (6 messages)
  thomas-only:  [1, 4]                        (2 messages)
  alice-only:   [2, 5]                        (2 messages)
  bob-only:     [3, 6]                        (2 messages)
```

## Next Steps

1. ✅ Set up multiple filtered queues
2. ✅ Test with alternating publisher
3. ✅ Add consumers to each queue
4. ✅ Route to different systems based on filters (MQTT, HTTP, etc.)
5. ✅ Create complex filter expressions
6. ✅ Monitor queue counts and message flow

## Key Learnings

1. **Multicast** = One message → Multiple queues
2. **Each queue evaluates its own filter** independently
3. **all-messages queue** serves as audit/backup
4. **Filters are evaluated per-queue**, not at the address level
5. **No message loss** — messages go to all matching queues
