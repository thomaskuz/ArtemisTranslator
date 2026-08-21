# Message Transformation & Filtering Flow Guide

Complete end-to-end guide for transforming messages in NodeRed and filtering them in Artemis based on application properties.

## Architecture Overview

```
Publisher (Python)
    ↓ test.queue
Artemis
    ↓
NodeRed AMQP In
    ↓
Function Node (Parse & Transform)
    ├─ Extract commander from body
    ├─ Create transformed body
    └─ Set application_properties
    ↓
NodeRed AMQP Out
    ↓ filtered-thomas-queue (address)
Artemis
    ↓
Filtered Queue (Filter: commander = 'Thomas')
    ↓ Only "Thomas" messages arrive
Artemis Console / Consumers
```

## Prerequisites

- ✅ Docker Compose with Artemis, NodeRed, Mosquitto running
- ✅ Python environment with `python-qpid-proton` installed
- ✅ NodeRed with @meowwolf AMQP node installed

## Step 1: Create Filtered Queue in Artemis

### Configuration

1. Navigate to **http://localhost:8161** (Artemis Admin Console)
2. Click **Queues** tab
3. Click **Create Queue** button
4. Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `filtered-thomas-queue` |
| **Address** | `filtered-thomas-queue` |
| **Routing type** | `Anycast` |
| **Filter** | `commander = 'Thomas'` |
| **Durable** | ✅ `true` |

5. Click **Create**

### What the Filter Does

```
Filter: commander = 'Thomas'
```

- ✅ Messages with `commander = "Thomas"` → PASS through
- ❌ Messages with `commander = "Alice"` → FILTERED OUT
- ❌ Messages without commander property → FILTERED OUT

## Step 2: Configure NodeRed Transformation Flow

### 2a. AMQP In Node (Receive)

1. Drag **AMQP In** node to canvas
2. Double-click to configure:
   - **Broker**: `Artemis Test env` (or your endpoint)
   - **Queue**: `test.queue`
   - **Auto-acknowledge**: ✅ checked
3. Name it: "Receive from test.queue"

### 2b. Function Node (Transform)

1. Drag **Function** node to canvas
2. Connect: AMQP In → Function
3. Double-click Function and paste this code:

```javascript
// Parse incoming message body
const incomingBody = JSON.parse(msg.payload.body);

// Extract commander and other data
const commander = incomingBody.commander || "Unknown";
const messageNumber = incomingBody.message_number || 0;

// Create transformed message with proper wrapped format
msg.payload = {
    body: JSON.stringify({
        original: incomingBody,
        transformation_status: "success",
        transformed_at: new Date().toISOString()
    }),
    application_properties: {
        commander: commander,
        message_number: messageNumber,
        transformed: true,
        source: "NodeRed-transformer"
    }
};

return msg;
```

4. Name it: "Parse & Transform"

### 2c. AMQP Out Node (Send)

1. Drag **AMQP Out** node to canvas
2. Connect: Function → AMQP Out
3. Double-click to configure:
   - **Broker**: `Artemis Test env`
   - **Address**: `filtered-thomas-queue` ← IMPORTANT!
   - **Autosettle**: ✅ checked
   - **Dynamic**: checked
   - **Sender settle mode**: `mixed`
   - **Receiver settle mode**: `first`
   - **Durable**: `none`
4. Name it: "Send to Filtered Queue"

### Complete Flow

```
[Receive from test.queue] → [Parse & Transform] → [Send to Filtered Queue]
```

## Step 3: Test with Alternating Publisher

### Run the Publisher

```bash
python simple_publisher_alternating_amqp.py
```

Output shows alternating commanders:
```
[✓] Sent message #1
    Commander: Thomas
    Body: {"commander":"Thomas","message_number":1,"sequence":1}

[✓] Sent message #2
    Commander: Alice
    Body: {"commander":"Alice","message_number":2,"sequence":1}

[✓] Sent message #3
    Commander: Thomas
    Body: {"commander":"Thomas","message_number":3,"sequence":2}
```

### Deploy NodeRed Flow

1. Click **Deploy** button (red, top-right)
2. Verify all nodes show green (connected/ready)

### Verify in Artemis Console

1. Go to **http://localhost:8161**
2. Click **Queues** tab
3. Check **filtered-thomas-queue**:
   - Should see messages arriving
   - Message count incrementing
   - **Only** messages with commander="Thomas" appear

4. Click on a message to view details:
   - **Body**: Contains transformed data
   - **Properties section**:
     - `applicationProperties.commander: Thomas`
     - `applicationProperties.transformed: true`
     - `applicationProperties.message_number: 1` (or 3, 5, etc.)

## Expected Results

### Messages That Arrive (✅)
```
Message #1: commander: Thomas → PASSES filter
Message #3: commander: Thomas → PASSES filter
Message #5: commander: Thomas → PASSES filter
Message #7: commander: Thomas → PASSES filter
```

### Messages That Are Filtered Out (❌)
```
Message #2: commander: Alice → FILTERED (doesn't match)
Message #4: commander: Alice → FILTERED (doesn't match)
Message #6: commander: Alice → FILTERED (doesn't match)
Message #8: commander: Alice → FILTERED (doesn't match)
```

## Understanding the Flow

### 1. Publisher Sends
```json
{
  "commander": "Thomas",
  "message_number": 1,
  "sequence": 1
}
```

### 2. AMQP In Receives (test.queue)
- Message arrives wrapped in NodeRed format
- Contains body + metadata

### 3. Function Transforms
- Parses JSON body
- Extracts commander value
- Wraps in proper AMQP format with `application_properties`

### 4. AMQP Out Sends (filtered-thomas-queue)
- Message sent to filtered queue
- Artemis evaluates filter: `commander = 'Thomas'`

### 5. Artemis Filter
- If commander = "Thomas" → Message accepted ✅
- Otherwise → Message rejected/dropped ❌

## Filter Syntax Reference

### Basic Syntax
```
propertyName = value
```

### Examples
```
commander = 'Thomas'                      # Exact match
message_number > 5                        # Greater than
message_number <= 10                      # Less than or equal
commander = 'Thomas' AND transformed = true  # AND logic
commander = 'Thomas' OR commander = 'Alice'  # OR logic
NOT commander = 'Bob'                     # NOT logic
commander LIKE 'Th%'                      # Pattern matching
```

### Special Characters
If property names have dots or hyphens, use quotes:
```
"app.config" = 'value'
"source-system" = 'NodeRed'
```

## Troubleshooting

### No Messages in Filtered Queue

**Problem:** Publisher is running, but filtered queue is empty.

**Solutions:**
1. ✅ Check AMQP Out node address is `filtered-thomas-queue`
2. ✅ Verify filter is: `commander = 'Thomas'` (with quotes)
3. ✅ Restart NodeRed flow (click Deploy)
4. ✅ Check test.queue has messages (verify transformation is happening)

### All Messages Filtered Out

**Problem:** Messages arrive in Artemis but not in filtered queue.

**Solutions:**
1. ✅ Verify application_properties are being set (check with consumer)
2. ✅ Check property name matches filter: `commander` not `cmd`
3. ✅ Verify value is exact: `'Thomas'` not `'thomas'`
4. ✅ Check for quotes in filter expression

### Messages Not Being Transformed

**Problem:** Messages appear in transform.queue without body or properties.

**Solutions:**
1. ✅ Check Function node code for syntax errors
2. ✅ Verify wrapped format: `msg.payload = { body: "...", application_properties: {...} }`
3. ✅ Check underscore in `application_properties` (not camelCase)
4. ✅ Run consumer to verify what's actually being sent

## Advanced: Multiple Filters

To filter by multiple properties:

### Create Multiple Filtered Queues

**Queue 1: thomas-queue**
- Filter: `commander = 'Thomas'`

**Queue 2: alice-queue**
- Filter: `commander = 'Alice'`

**Queue 3: high-priority-queue**
- Filter: `commander = 'Thomas' AND message_number > 10`

### Multiple Publishers

Modify `simple_publisher_alternating_amqp.py` to add more commanders:

```python
self.commanders = ["Thomas", "Alice", "Bob"]  # Add more names
```

## Key Learnings

1. **Filter Syntax**: Reference properties directly by name, not with `applicationProperties.` prefix
2. **Message Format**: AMQP In/Out nodes require wrapped format: `msg.payload = { body: "...", application_properties: {...} }`
3. **Property Location**: Application properties must be nested in `msg.payload.application_properties`
4. **Testing**: Use alternating values to easily verify filters work
5. **Artemis Console**: Check message properties in UI to verify what's actually sent

## Next Steps

1. ✅ Test with different filter values
2. ✅ Create multiple filtered queues for different commanders
3. ✅ Add more complex filter expressions
4. ✅ Connect consumers to read filtered messages
5. ✅ Forward to MQTT or other systems based on filters
