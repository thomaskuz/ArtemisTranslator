# NodeRed Scripts - Complete Transformation Pipeline

Comprehensive transformation pipeline for converting AMQP messages to CloudEvents v1.0 format with production-ready reliability features.

## Complete Flow Architecture

```
AMQP In (Artemis)
    ↓ [FM2/v260819 - FileManager Status]
Prepare Body (prepareBody.js)
    ├─ Recursively parses JSON strings
    └─ Handles deeply nested structures
    ↓
Setup CloudEvent (setupCloudEvent.js)
    ├─ Transforms to FASC format
    └─ Creates CloudEvent v1.0 wrapper
    ↓
Store & Forward (StoreForward.js) [PRODUCTION]
    ├─ Queues during disconnection
    └─ Flushes when reconnected
    ↓
Rate Limit [PRODUCTION]
    ├─ Controls throughput
    └─ Prevents overload
    ↓
MQTT Out (Mosquitto/HiveMQ)
    ↓ [FASC_260819 - FileActionStatusChanged]
```

## Scripts Overview

### 1. prepareBody.js
**Purpose:** Extract and recursively parse message body from AMQP

**Input:**
- `msg.payload.body` — JSON string or object (from AMQP In)

**Processing:**
- Extracts body from AMQP message structure
- Recursively parses nested JSON strings
- Handles any JSON structure dynamically
- Field-agnostic (no hardcoded field names)

**Output:**
- `msg.parsedBody` — Fully parsed object (all nested strings converted to objects)
- `msg.payload.body` — Updated with parsed content (for pipeline flow)
- `msg.rawBody` — Original body string (for debugging)
- `msg.bodyParsed` — Success flag
- Status indicator: 🟢 Success / 🔴 Error

**Key Feature:** Deep parsing handles complex nested JSON strings at any depth

---

### 2. setupCloudEvent.js
**Purpose:** Transform parsed body into CloudEvents v1.0 format (FASC structure)

**Input:**
- `msg.parsedBody` — From prepareBody (required)
- `msg.topic` (optional) — MQTT topic

**Processing:**
- Generates unique UUID for event ID
- Creates CloudEvent v1.0 wrapper with FASC structure
- Returns clean message with only payload and topic

**Output:** 
- `msg.payload` — Stringified CloudEvent JSON only
- `msg.topic` — MQTT topic for publish

**CloudEvent Structure (FASC format):**
```json
{
  "specversion": "1.0",
  "type": "imec.event.file_action_status_changed",
  "source": "urn:imec:ot:artemis:file-transfer-server",
  "subject": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged",
  "id": "uuid-generated",
  "time": "timestamp-in-ms",
  "datacontenttype": "application/json",
  "dataschema": "https://schemas.imec.be/imec.event.file_action_status_changed.v1.json",
  "data": { /* full parsed body from FM2 */ }
}
```

**Status indicator:** 🟢 Success / 🔴 Error

---

### 3. StoreForward.js [PRODUCTION]
**Purpose:** Queue messages during MQTT disconnection, flush when reconnected

**Input:**
- Regular messages → passed through when gate is open
- Control messages → manage gate state

**Processing:**
- Gate open: passes messages through immediately
- Gate closed: queues messages (max 100)
- On reconnection: flushes entire queue

**Control Commands:**
- `{ topic: 'control', payload: 'open' }` — Open gate, flush queue
- `{ topic: 'control', payload: 'queue' }` — Close gate, start queuing

**Usage:** Prevents message loss during network interruptions

---

### 4. StatusCheck.js [PRODUCTION]
**Purpose:** Monitor MQTT connection status and manage Store & Forward gate

**Input:**
- MQTT status events (from MQTT Out node)
- Heartbeat signals (every 10 seconds)

**Processing:**
- Tracks MQTT connection state
- Sends control signals to Store & Forward
- Triggers reconnection on failure

**Output:**
- Control messages to StoreForward (open/queue gate)
- Reconnect triggers on disconnection

**Usage:** Automates gate management based on connection health

---

## Message Structure References

### Source Format: FM2/v260819
**Path:** `ExampleMessages/SourceMessages/FM2/v260819`

```json
{
  "durable": true,
  "priority": 4,
  "to": "IMEC.LEUVEN.FAB2.Development.FileManager.Server.Event.StatusUpdate",
  "body": "{\"header\":{...},\"metadata\":{...},\"originalRequest\":{...},\"status\":\"ERROR\",\"error\":{...}}"
}
```

**Type:** FileManager Request Status Update
**Processing:** prepareBody recursively parses the nested JSON body

---

### Destination Format: FASC_260819
**Path:** `ExampleMessages/DestinationMessages/FASC_260819.json`

```json
{
  "specversion": "1.0",
  "type": "imec.event.file_action_status_changed",
  "source": "urn:imec:ot:artemis:file-transfer-server",
  "subject": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged",
  "id": "uuid",
  "time": "timestamp-ms",
  "datacontenttype": "application/json",
  "dataschema": "https://schemas.imec.be/imec.event.file_action_status_changed.v1.json",
  "data": { /* parsed FileManager data */ }
}
```

**Type:** File Action Status Changed (FASC) CloudEvent
**Source:** Transformed from FM2 by setupCloudEvent.js

---

## Complete NodeRed Flow Setup

### Flow Structure
```
Inject/AMQP In → Prepare Body → Setup CloudEvent → Store & Forward → Rate Limit → MQTT Out
                                                          ↑
                                                   StatusCheck ← MQTT Status
```

### Node Configuration

#### 1. AMQP In (or Inject for testing)
```
Queue: transform.queue
Broker: Artemis (amqp://admin:admin@localhost:5672)
Auto-acknowledge: ✅
```

Test payload (Inject node):
```json
{
  "durable": true,
  "priority": 4,
  "to": "IMEC.LEUVEN.FAB2.Development.FileManager.Server.Event.StatusUpdate",
  "body": "{\"header\":{\"correlationSystem\":\"CIRCL_2\",...},\"metadata\":{...},...}"
}
```

#### 2. Prepare Body (Function Node)
Copy entire code from `prepareBody.js`

**Output:** msg.parsedBody (object with all nested strings parsed)

#### 3. Setup CloudEvent (Function Node)
Copy entire code from `setupCloudEvent.js`

**Output:** msg.payload (stringified CloudEvent), msg.topic (MQTT topic)

#### 4. Store & Forward (Function Node) [PRODUCTION]
Copy entire code from `StoreForward.js`

**Configuration:**
- Input from Setup CloudEvent
- Output to Rate Limit
- Receives control messages from StatusCheck

#### 5. Rate Limit (Built-in Node) [PRODUCTION]
- Rate: 10 msgs/sec (adjustable)
- Action: Drop excess

#### 6. Status Check (Function Node) [PRODUCTION]
Copy entire code from `StatusCheck.js`

**Configuration:**
- Input: MQTT Status node + 10s heartbeat
- Output: Control messages to Store & Forward

#### 7. MQTT Out
```
Topic: msg.topic
Broker: Mosquitto (localhost:1883)
QoS: 1 (at least once)
Retain: false
```

---

## Data Flow Example

**Input (FM2):**
```json
{
  "body": "{\"header\":{\"correlationSystem\":\"CIRCL_2\",\"correlationId\":\"62\",...},\"originalRequest\":{...},\"status\":\"ERROR\",\"error\":{...},\"metadata\":{...}}"
}
```

**After prepareBody:**
```json
{
  "parsedBody": {
    "header": {"correlationSystem": "CIRCL_2", "correlationId": "62", ...},
    "originalRequest": { ... },
    "status": "ERROR",
    "error": { ... },
    "metadata": { ... }
  }
}
```

**After setupCloudEvent:**
```json
{
  "payload": "{\"specversion\":\"1.0\",\"type\":\"imec.event.file_action_status_changed\",...,\"data\":{...}}",
  "topic": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged"
}
```

**Published to MQTT:** CloudEvent JSON (FASC_260819 format)

---

## Testing & Validation

### Local Testing
1. Use Inject node with FM2 test data
2. Debug at each stage:
   - After Prepare Body: Check `msg.parsedBody` is object
   - After Setup CloudEvent: Check `msg.payload` is CloudEvent string
   - After MQTT Out: Verify message published

### Production Testing
1. Connect to real Artemis AMQP
2. Monitor MQTT Status node
3. Test Store & Forward:
   - Disconnect MQTT broker
   - Verify messages queue
   - Reconnect broker
   - Verify queue flushes

---

## Key Characteristics

### Deep Parsing
- Recursively parses JSON strings at any nesting level
- Field-agnostic (works with any JSON structure)
- Handles variable data formats

### CloudEvent Transformation
- Standard v1.0 format
- FASC event type and schema
- Complete data preservation
- Unique UUIDs per message

### Production Reliability
- Automatic message queuing on disconnection
- Controlled throughput with rate limiting
- Health monitoring and reconnection
- No message loss during network issues

---

## Files in This Directory

- `prepareBody.js` — Body extraction and recursive JSON parsing
- `setupCloudEvent.js` — CloudEvent creation (FASC format)
- `StoreForward.js` — Message queueing during disconnection
- `StatusCheck.js` — Connection monitoring and gate control
- `README.md` — This documentation

## Related Files

**Source Examples:**
- `../../ExampleMessages/SourceMessages/FM2/v260819` — FileManager status message

**Destination Examples:**
- `../../ExampleMessages/DestinationMessages/FASC_260819.json` — CloudEvent output

## Next Steps

1. Copy scripts into NodeRed Function nodes
2. Wire the complete flow (local testing first)
3. Deploy to Artemis → MQTT pipeline
4. Monitor MQTT Status for production health
5. Adjust Rate Limit threshold as needed
