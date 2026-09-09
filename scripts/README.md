# AMQP & MQTT Scripts

Collection of Python scripts for testing and interacting with Artemis message broker via AMQP and MQTT protocols.

## Quick Start

### Install Dependencies
```bash
pip install python-qpid-proton paho-mqtt
```

### Run a Script
```bash
python scripts/simple_publisher_amqp.py
```

---

## AMQP Publishers

### `simple_publisher_amqp.py`
**Sends simple JSON messages via AMQP**

- Sends every 5 seconds
- Payload: `{"color": "Red", "message_number": N}`
- Address: `amqp-mqtt-bridge`
- Use case: Basic message flow testing

```bash
python scripts/simple_publisher_amqp.py
```

### `simple_publisher_alternating_amqp.py`
**Sends alternating messages with different commanders**

- Alternates between commanders: Thomas, Alice, Bob
- Every 5 seconds
- Use case: Testing filters and routing

```bash
python scripts/simple_publisher_alternating_amqp.py
```

### `publisher_amqp.py`
**Generic publisher with configurable messages**

- Sends every 5 seconds
- Message: "Hello from Artemis (#N)"
- Address: `amqp-mqtt-bridge`
- Use case: General-purpose publishing

```bash
python scripts/publisher_amqp.py
```

### `publisher_with_headers_amqp.py`
**Publisher with AMQP message headers**

- Sends with standard AMQP headers (ID, subject, correlation ID, etc.)
- Custom application properties
- Every 5 seconds
- Use case: Testing header-based filters

```bash
python scripts/publisher_with_headers_amqp.py
```

### `publisher_with_headers_extended_amqp.py`
**Publisher with ALL types of AMQP metadata**

- Demonstrates:
  - Standard AMQP message properties
  - AMQP headers (priority, TTL, timestamp)
  - Custom application properties
- Every 5 seconds
- Output: Detailed metadata display
- Use case: Understanding AMQP message structure

```bash
python scripts/publisher_with_headers_extended_amqp.py
```

---

## AMQP Consumers

### `consumer_amqp.py`
**Simple consumer - receives ALL messages**

- Connects to queue: `test`
- Receives historical + new messages
- No filtering
- Displays each message as received
- Use case: Monitoring message flow

```bash
python scripts/consumer_amqp.py
```

### `consumer_with_filter_amqp.py`
**Consumer with AMQP selector filtering**

- Supports AMQP selector expressions
- Filter by application properties
- Examples: `commander = 'Thomas'`, `message_number > 5`
- Receives all matching messages from queue
- Use case: Selective message consumption

```bash
# Edit the script to set your filter:
# filter_expr = "commander = 'Thomas'"

python scripts/consumer_with_filter_amqp.py
```

**Selector Examples:**
```python
filter_expr = "commander = 'Thomas'"                    # Exact match
filter_expr = "message_number > 5"                      # Greater than
filter_expr = "commander IN ('Thomas', 'Alice')"        # Multiple values
filter_expr = "commander = 'Thomas' AND message_number > 3"  # AND logic
```

---

## MQTT

### `mqtt_publisher.py`
**MQTT publisher - sends messages to MQTT broker**

- Connects to: `localhost:1883`
- Publishes to: `amqp-mqtt-bridge`
- Credentials: `admin:admin`
- Sends every 5 seconds
- Payload: `{"color": "Red", "message_number": N, "timestamp": T}`
- Use case: Testing MQTT-to-MQTT messaging

```bash
python scripts/mqtt_publisher.py
```

### `mqtt_subscriber.py`
**MQTT subscriber - receives messages from MQTT broker**

- Connects to: `localhost:1883`
- Subscribes to: `amqp-mqtt-bridge`
- Credentials: `admin:admin`
- Receives messages in CloudEvent format (from AMQP→MQTT bridge)
- Use case: Testing AMQP-MQTT bridging or MQTT-to-MQTT messaging

```bash
python scripts/mqtt_subscriber.py
```

---

## Typical Workflows

### Test 1: AMQP Publishing (No Consumer)

**Terminal:**
```bash
python scripts/simple_publisher_amqp.py
```

**Check in Artemis Console:** http://localhost:8161 → Queues → `amqp-mqtt-bridge`

### Test 2: AMQP Publishing + AMQP Consuming

**Terminal 1 (Publisher):**
```bash
python scripts/simple_publisher_amqp.py
```

**Terminal 2 (Consumer):**
```bash
python scripts/consumer_amqp.py
```

### Test 3: AMQP-MQTT Bridging

**Terminal 1 (MQTT Subscriber):**
```bash
python scripts/mqtt_subscriber.py
```

**Terminal 2 (AMQP Publisher):**
```bash
python scripts/simple_publisher_amqp.py
```

MQTT subscriber receives AMQP messages in real-time! ✅

### Test 4: Filtered Consumption

**Terminal 1 (Publisher - sends Thomas + Alice alternating):**
```bash
python scripts/simple_publisher_alternating_amqp.py
```

**Terminal 2 (Consumer with filter - only Thomas):**

Edit `consumer_with_filter_amqp.py`:
```python
filter_expr = "commander = 'Thomas'"
```

```bash
python scripts/consumer_with_filter_amqp.py
```

Only Thomas messages are received! ✅

### Test 5: AMQP Headers & Metadata

**Terminal:**
```bash
python scripts/publisher_with_headers_extended_amqp.py
```

See all types of AMQP metadata displayed with each message.

### Test 6: MQTT-to-MQTT Messaging

**Terminal 1 (MQTT Publisher):**
```bash
python scripts/mqtt_publisher.py
```

**Terminal 2 (MQTT Subscriber):**
```bash
python scripts/mqtt_subscriber.py
```

MQTT publisher sends messages → Artemis MQTT broker → MQTT subscriber receives them! ✅

### Test 7: MQTT Publisher with AMQP Consumer

**Terminal 1 (MQTT Publisher):**
```bash
python scripts/mqtt_publisher.py
```

**Terminal 2 (AMQP Consumer):**
```bash
python scripts/consumer_amqp.py
```

Note: MQTT publisher → Artemis MQTT → Queue on address.
AMQP consumer might not receive (depends on address configuration).
For this to work, need MQTT-to-AMQP bridging (different setup).

---

## Message Formats

### Simple Publisher Output
```json
{
  "color": "Red",
  "message_number": 1
}
```

### With Headers
```json
{
  "body": "{...}",
  "properties": {
    "commander": "Thomas",
    "message_number": 1,
    "custom_header_1": "custom_value_1"
  }
}
```

### CloudEvent (AMQP→MQTT Bridge)
```json
{
  "specversion": "1.0",
  "type": "imec.event.file_action_status_changed",
  "source": "urn:imec:ot:artemis:file-transfer-server",
  "subject": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged",
  "id": "uuid-generated",
  "time": "2024-08-21T10:30:45.123Z",
  "datacontenttype": "application/json",
  "data": {...}
}
```

---

## Configuration

### Artemis Connection
- **AMQP Broker:** `amqp://admin:admin@localhost:5672`
- **MQTT Broker:** `localhost:1883`
- **Credentials:** `admin:admin`

### Default Addresses/Queues
- **Address:** `amqp-mqtt-bridge` (Multicast)
- **Queue:** `test` (on amqp-mqtt-bridge address)

### Port Mappings
- **5672** → AMQP
- **1883** → MQTT
- **8161** → Artemis Admin Console

---

## Troubleshooting

### "Connection refused"
- Verify Artemis is running: `docker-compose ps`
- Check port (5672 for AMQP, 1883 for MQTT)

### "Auth failed" (MQTT)
- Credentials must be: `admin:admin`
- Check docker-compose environment variables

### "Queue not found"
- Verify queue exists in Artemis Console
- Or let Artemis auto-create (though Anycast by default)

### "No messages received"
- Check publisher is actually sending (look for output)
- Verify queue/address name matches
- Check filters aren't too restrictive

---

## Script Order (By Complexity)

### AMQP Scripts
1. `simple_publisher_amqp.py` — Start here
2. `consumer_amqp.py` — Receive messages
3. `simple_publisher_alternating_amqp.py` — Test with variations
4. `consumer_with_filter_amqp.py` — Add filtering
5. `publisher_with_headers_amqp.py` — Add metadata
6. `publisher_with_headers_extended_amqp.py` — Full complexity

### MQTT Scripts
1. `mqtt_publisher.py` — Start here (MQTT publish)
2. `mqtt_subscriber.py` — Receive MQTT messages
3. Test with AMQP publishers for bridging

### Combined Testing
- AMQP→MQTT: Run AMQP publisher + MQTT subscriber
- MQTT→MQTT: Run MQTT publisher + MQTT subscriber
- MQTT→AMQP: (Different setup needed)

---

## Dependencies

```bash
pip install python-qpid-proton paho-mqtt
```

- `python-qpid-proton` — AMQP protocol support
- `paho-mqtt` — MQTT protocol support

---

## Related Documentation

- [AMQP-MQTT Bridging Guide](../guides/amqp-mqtt-bridging.md)
- [AMQP Multicast/Anycast Behavior](../guides/amqp-multicast-anycast-behavior.md)
- [AMQP Selectors & Filtering](../guides/amqp-selectors-filtering.md)
- [Data Contracts](../DataContracts.md)
