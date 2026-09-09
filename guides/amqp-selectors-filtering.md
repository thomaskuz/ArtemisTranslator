# AMQP Selectors and Message Filtering

Guide to using AMQP selector filters to receive only specific messages from Artemis queues.

## What are AMQP Selectors?

**AMQP Selectors** are filter expressions evaluated **at the broker level** (not client-side). They allow you to specify which messages you want to receive when consuming from a queue.

```
All Messages in Queue
├─ Message 1 (commander='Thomas')
├─ Message 2 (commander='Alice')
├─ Message 3 (commander='Thomas')
└─ Message 4 (commander='Bob')

Consumer with selector: commander = 'Thomas'
├─ Receives: Message 1 ✅
├─ Receives: Message 3 ✅
├─ Skips: Message 2 ❌
└─ Skips: Message 4 ❌
```

### Key Advantages

- ✅ **Broker-level filtering** — Only matching messages sent to consumer
- ✅ **Reduces network traffic** — Non-matching messages stay in queue
- ✅ **Reduces client processing** — Client doesn't see unwanted messages
- ✅ **Efficient** — Filtering happens on the broker (powerful hardware)
- ✅ **Similar to JMS** — Uses JMS message selector syntax

---

## Basic Selector Syntax

### String Comparison

```python
filter_expr = "commander = 'Thomas'"  # Exact match
```

**Rules:**
- Use **single quotes** for strings (not double quotes)
- Case-sensitive: `'Thomas'` ≠ `'thomas'`
- Property names are case-sensitive

### Numeric Comparison

```python
filter_expr = "message_number > 5"     # Greater than
filter_expr = "message_number >= 5"    # Greater than or equal
filter_expr = "message_number < 10"    # Less than
filter_expr = "message_number <= 10"   # Less than or equal
filter_expr = "message_number = 7"     # Equal
filter_expr = "message_number <> 7"    # Not equal
```

### Logical Operators

```python
# AND - both conditions must be true
filter_expr = "commander = 'Thomas' AND message_number > 5"

# OR - at least one condition must be true
filter_expr = "commander = 'Thomas' OR commander = 'Alice'"

# NOT - condition must be false
filter_expr = "NOT commander = 'Bob'"
```

### Pattern Matching (LIKE)

```python
# Matches strings starting with "Th"
filter_expr = "commander LIKE 'Th%'"

# Matches strings containing "om"
filter_expr = "commander LIKE '%om%'"

# % = any characters, _ = single character
filter_expr = "commander LIKE '_homas'"  # homas preceded by any char
```

### IN Operator (Multiple Values)

```python
# Matches any of the values
filter_expr = "commander IN ('Thomas', 'Alice', 'Bob')"
```

### IS NULL / IS NOT NULL

```python
filter_expr = "optional_field IS NULL"
filter_expr = "required_field IS NOT NULL"
```

---

## Using Selectors in Consumer Scripts

### With the New Script

```bash
python consumer_with_filter_amqp.py
```

Edit the script to uncomment the desired filter:

```python
def main():
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test"

    # Choose one:
    filter_expr = None  # No filter
    # filter_expr = "commander = 'Thomas'"
    # filter_expr = "message_number > 5"

    handler = ConsumerWithFilter(broker, queue, filter_expr)
    container = Container(handler)
    container.run()
```

### Example 1: Only Thomas Messages

```python
filter_expr = "commander = 'Thomas'"
```

**Result:**
```
[✓] Connected to Artemis
[✓] Listening on queue: test
[!] Filter applied: commander = 'Thomas'
[!] Will receive historical + new messages
[!] Press Ctrl+C to stop

[✓] Message 1 received:
    Properties: {'commander': 'Thomas', 'message_number': 1}
    Body: ...
```

### Example 2: High Priority Messages

```python
filter_expr = "priority >= 8"
```

Only messages with priority 8 or higher are received.

### Example 3: Multiple Conditions

```python
filter_expr = "commander = 'Thomas' AND message_number > 10"
```

Only Thomas's messages where message_number is greater than 10.

### Example 4: Any of Multiple Values

```python
filter_expr = "commander IN ('Thomas', 'Alice')"
```

Messages from Thomas OR Alice (but not Bob).

---

## Common Selector Patterns

### By User/Commander

```python
filter_expr = "commander = 'Alice'"
```

### By Priority Range

```python
filter_expr = "priority >= 5 AND priority <= 8"
```

### By Status

```python
filter_expr = "status = 'ERROR'"
filter_expr = "status = 'PENDING' OR status = 'IN_PROGRESS'"
```

### By Source System

```python
filter_expr = "source = 'FileManager'"
```

### By Time Window (if stored as number)

```python
filter_expr = "timestamp > 1629000000"  # Unix timestamp
```

### Complex: Business Logic

```python
filter_expr = "(commander = 'Thomas' OR commander = 'Alice') AND priority > 5"
```

---

## Selector Limitations

### What Selectors Can Filter On

✅ **Application Properties** — Custom headers you add
```python
msg.properties["commander"] = "Thomas"
```

✅ **Standard AMQP Properties** (if set)
```python
msg.priority = 7
msg.correlation_id = "corr-123"
```

### What Selectors CANNOT Filter On

❌ **Message Body** — Content of the message
❌ **Encoded data** — Raw binary/JSON
❌ **Custom objects** — Application-specific types

**Workaround:** Use application properties instead of embedding filter data in body.

---

## Practical Example: CloudEvent Filtering

If you're receiving CloudEvent messages from your transformation pipeline, you might filter by:

```python
# Only ERROR events
filter_expr = "error IS NOT NULL"

# Only specific event types
filter_expr = "type = 'imec.event.file_action_status_changed'"

# Only recent events (if stored as timestamp)
filter_expr = "timestamp > 1629000000"
```

---

## Broker Configuration (Artemis)

### Queue-Level Selectors

You can also set selectors at the **queue creation** level in Artemis:

**Artemis Console:**
1. **Queues** → **Create Queue**
2. Fill in:
   - **Name:** `thomas-queue`
   - **Address:** `events`
   - **Filter:** `commander = 'Thomas'` ← Queue-level filter

**Result:** Only Thomas messages stored in this queue

### Consumer-Level vs Queue-Level Selectors

| Aspect | Queue-Level | Consumer-Level |
|--------|------------|----------------|
| **Where** | Set when creating queue | Set when connecting consumer |
| **Persisted** | Messages not matching filter don't enter queue | All messages in queue, consumer filters |
| **Use Case** | Different queues for different topics | One queue, multiple consumers |
| **Storage** | Only matching messages stored | All messages stored |

---

## Testing Selectors

### Test 1: Basic String Filter

**Setup:**
```python
filter_expr = "commander = 'Thomas'"
```

**Publish messages:**
```bash
python simple_publisher_amqp.py  # Publishes with color='Red'
```

**Expected:**
- Consumer receives messages (if they have the property)
- If property not set, messages skipped

### Test 2: Numeric Filter

**Setup:**
```python
filter_expr = "message_number > 5"
```

**Expected:**
- Messages 1-5: skipped
- Messages 6+: received

### Test 3: No Filter

**Setup:**
```python
filter_expr = None
```

**Expected:**
- All messages received

---

## Troubleshooting

### Problem: Selector Not Working

**Solution:**
1. ✅ Verify property names match exactly (case-sensitive)
2. ✅ Check string values use single quotes: `'Thomas'` not `"Thomas"`
3. ✅ Verify property is actually set on messages
4. ✅ Check queue has messages matching selector

### Problem: No Messages Received

**Possible causes:**
1. ❌ Filter is too restrictive (no messages match)
2. ❌ Property name doesn't exist on messages
3. ❌ Using wrong quote type (double instead of single)
4. ❌ Queue is empty

**Debug:**
1. Run consumer with `filter_expr = None` to verify messages exist
2. Check message properties in Artemis Console
3. Simplify selector to verify syntax

### Problem: Syntax Error

**Error:** `"Selector parsing error"`

**Solution:**
1. ✅ Check quotes: `'value'` not `"value"`
2. ✅ Check operators: `=` not `==`
3. ✅ Check property names (no special chars)
4. ✅ Verify parentheses match: `(a = 'x' AND b > 5)`

---

## Performance Considerations

### When Selectors Help
✅ Filter out 90% of messages (broker does work once)
✅ Network bandwidth limited (reduce message traffic)
✅ Client has limited processing power (broker filters)

### When Selectors Don't Help
❌ Filter out only 5% (mostly send everything anyway)
❌ Have one consumer reading 100% of messages (no reduction)
❌ Body-based filtering (selectors can't filter bodies)

---

## AMQP Selector vs Artemis Queue Filter

### Artemis Queue Filter
```
Set when creating queue
Applied permanently to queue
All consumers on that queue get pre-filtered messages
Filters: commander = 'Thomas'
```

### AMQP Selector (Consumer-Level)
```
Set when creating consumer/receiver
Applied to this consumer only
Other consumers on same queue can have different selectors
Selectors: message_number > 5
```

**They work together:**
```
Queue "thomas-messages"
├─ Queue Filter: commander = 'Thomas'
├─ Consumer A with Selector: message_number > 10
│  └─ Receives: Thomas messages with number > 10
├─ Consumer B with Selector: message_number <= 10
│  └─ Receives: Thomas messages with number <= 10
└─ Consumer C with no Selector
   └─ Receives: All Thomas messages
```

---

## Complete Working Example

**File:** `consumer_with_filter_amqp.py`

**Usage:**

```bash
# Edit the script to set your filter:
# filter_expr = "commander = 'Thomas'"

python consumer_with_filter_amqp.py
```

**Output:**
```
[✓] Connected to Artemis
[✓] Listening on queue: test
[!] Filter applied: commander = 'Thomas'
[!] Will receive historical + new messages
[!] Press Ctrl+C to stop

[✓] Message 1 received:
    Properties: {'commander': 'Thomas', 'message_number': 1}
    Body: {...}
```

---

## Reference: All Selector Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `=` | Equal | `field = 'value'` |
| `<>` | Not equal | `field <> 'value'` |
| `>` | Greater than | `count > 5` |
| `<` | Less than | `count < 5` |
| `>=` | Greater or equal | `count >= 5` |
| `<=` | Less or equal | `count <= 5` |
| `LIKE` | Pattern match | `name LIKE 'Jo%'` |
| `IN` | Multiple values | `status IN ('A', 'B')` |
| `IS NULL` | Field is null | `optional IS NULL` |
| `IS NOT NULL` | Field exists | `required IS NOT NULL` |
| `AND` | Both true | `a = 'x' AND b > 5` |
| `OR` | At least one true | `a = 'x' OR b = 'x'` |
| `NOT` | Negate | `NOT status = 'DONE'` |

---

## Next Steps

1. ✅ Review the selector syntax
2. ✅ Update `consumer_with_filter_amqp.py` with your desired filter
3. ✅ Run the consumer to test filtering
4. ✅ Compare filtered results with unfiltered (use `filter_expr = None`)
5. ✅ Combine with queue-level filters for multi-tier filtering
