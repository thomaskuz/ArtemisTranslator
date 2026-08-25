# Data Contracts - Transformation Pipeline

Complete specification of data flow, formats, and transformations for the Artemis AMQP → MQTT pipeline.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION FLOW                        │
└─────────────────────────────────────────────────────────────────┘

AMQP In                 Prepare Body            Setup CloudEvent
(FM2/v260819)      +    (Parse JSON)       +    (Add metadata)
     │                      │                        │
     └──────────────────────┴────────────────────────┘
                            │
                     msg.parsedBody
                     msg.payload (input)
                            │
                    ┌───────┴────────┐
                    │                │
            Store & Forward      Rate Limit
            (Queue on disconnect)  (Throttle)
                    │                │
                    └───────┬────────┘
                            │
                    msg.payload (CloudEvent)
                    msg.topic (MQTT topic)
                            │
                        MQTT Out
                      (Publish)
                            │
                    MQTT Broker (FASC_260819)
```

---

## Node 1: AMQP In (Artemis Receiver)

### Contract: Input Source

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `to` | String | Message property | Destination address (e.g., "IMEC.LEUVEN.FAB2...") |
| `body` | String | Message body | JSON as string (nested, may contain escaped quotes) |
| `durable` | Boolean | Message property | Durability flag |
| `priority` | Number | Message property | Message priority (0-9) |

### Example Input
```json
{
  "durable": true,
  "priority": 4,
  "to": "IMEC.LEUVEN.FAB2.Development.FileManager.Server.Event.StatusUpdate",
  "body": "{\"header\":{\"correlationSystem\":\"CIRCL_2\",\"correlationId\":\"62\",\"timestamp\":\"2024-08-21T10:30:45Z\"},\"originalRequest\":{\"fileId\":\"file-123\",\"operation\":\"upload\"},\"status\":\"ERROR\",\"error\":{\"code\":\"EACCES\",\"message\":\"Permission denied\"},\"metadata\":{\"source\":\"FileManager\",\"version\":\"1.0\"}}"
}
```

### Source File Reference
- **Path:** `ExampleMessages/SourceMessages/FM2/v260819`
- **Format:** FileManager Request Status Update
- **Description:** Status updates from FileManager service with nested JSON body

### Output to Next Node
```
msg.payload = {
  durable: true,
  priority: 4,
  to: "...",
  body: "{...}"  // Exact input, passed through
}
```

---

## Node 2: prepareBody.js (Function)

### Purpose
Extract and recursively parse the nested JSON string in `msg.payload.body`. Artemis AMQP messages often have deeply nested JSON strings; this node converts them to proper objects.

### Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `msg.payload.body` | String | ✅ Yes | JSON string, may be nested |
| `msg.payload.durable` | Boolean | ❌ No | Passed through unchanged |
| `msg.payload.to` | String | ❌ No | Passed through unchanged |

### Processing Rules

1. **Extract:** Get `msg.payload.body`
2. **Type Check:** Is it a string? Parse with `JSON.parse()`
3. **Recursive Parse:** For each field in parsed object:
   - If value is string AND valid JSON → recursively parse
   - If value is object/array → recursively check each item
   - If value is primitive → keep as-is
4. **Continue until:** No more nested JSON strings found

### Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `msg.parsedBody` | Object | Fully parsed object (all nested strings → objects) |
| `msg.payload.body` | Object | Updated with parsed content (for pipeline flow) |
| `msg.rawBody` | String | Original body string (for debugging) |
| `msg.bodyParsed` | Boolean | Success flag (`true` = successful parse) |

### Example Transformation

**Input:**
```json
{
  "payload": {
    "body": "{\"header\":{\"correlationSystem\":\"CIRCL_2\"},\"status\":\"ERROR\",\"error\":\"{\\\"code\\\":\\\"EACCES\\\",\\\"message\\\":\\\"Permission denied\\\"}\"}"
  }
}
```

**Output:**
```json
{
  "parsedBody": {
    "header": {
      "correlationSystem": "CIRCL_2"
    },
    "status": "ERROR",
    "error": {
      "code": "EACCES",
      "message": "Permission denied"
    }
  },
  "payload": {
    "body": {
      "header": {"correlationSystem": "CIRCL_2"},
      "status": "ERROR",
      "error": {"code": "EACCES", "message": "Permission denied"}
    }
  },
  "rawBody": "{...original string...}",
  "bodyParsed": true
}
```

### Field-by-Field Mapping

| Source | Target | Transformation |
|--------|--------|-----------------|
| `msg.payload.body` (string) | `msg.parsedBody` (object) | Recursive JSON.parse() |
| `msg.payload.body` (string) | `msg.rawBody` (string) | Copy original before parsing |
| Parsing success | `msg.bodyParsed` (boolean) | Set to `true` |
| Other properties | Passed through | No change |

### Error Handling

| Scenario | Result | `msg.bodyParsed` |
|----------|--------|------------------|
| Valid JSON string | ✅ Parsed to object | `true` |
| Invalid JSON | ❌ Parse error | `false` |
| Empty string | ❌ Error | `false` |
| Non-string body | ❌ Type error | `false` |

### Debug Output
```
🟢 Body parsed successfully
or
🔴 Error parsing body: [error message]
```

---

## Node 3: setupCloudEvent.js (Function)

### Purpose
Transform the parsed body into CloudEvents v1.0 format with FASC (File Action Status Changed) metadata. This wraps the data in a standard event envelope.

### Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `msg.parsedBody` | Object | ✅ Yes | From prepareBody node |
| `msg.topic` | String | ❌ No | Optional MQTT topic override |

### Processing Rules

1. **Validate:** Check `msg.parsedBody` exists
2. **Generate ID:** Create unique UUID for `id` field
3. **Get timestamp:** Current time in milliseconds
4. **Build CloudEvent:** Create object with:
   - `specversion`: "1.0" (CloudEvents spec version)
   - `type`: "imec.event.file_action_status_changed"
   - `source`: "urn:imec:ot:artemis:file-transfer-server"
   - `subject`: "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged"
   - `id`: Generated UUID
   - `time`: ISO timestamp in milliseconds
   - `datacontenttype`: "application/json"
   - `dataschema`: "https://schemas.imec.be/imec.event.file_action_status_changed.v1.json"
   - `data`: The entire `msg.parsedBody`
5. **Stringify:** Convert CloudEvent to JSON string
6. **Set topic:** Use standard FASC topic path

### Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `msg.payload` | String | CloudEvent v1.0 JSON (stringified) |
| `msg.topic` | String | MQTT topic for publish |

### Example Transformation

**Input (`msg.parsedBody`):**
```json
{
  "header": {
    "correlationSystem": "CIRCL_2",
    "correlationId": "62"
  },
  "status": "ERROR",
  "error": {
    "code": "EACCES",
    "message": "Permission denied"
  }
}
```

**Output (`msg.payload`):**
```json
{
  "specversion": "1.0",
  "type": "imec.event.file_action_status_changed",
  "source": "urn:imec:ot:artemis:file-transfer-server",
  "subject": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged",
  "id": "a1b2c3d4-e5f6-4789-ab00-123456789abc",
  "time": "2024-08-21T10:30:45.123Z",
  "datacontenttype": "application/json",
  "dataschema": "https://schemas.imec.be/imec.event.file_action_status_changed.v1.json",
  "data": {
    "header": {"correlationSystem": "CIRCL_2", "correlationId": "62"},
    "status": "ERROR",
    "error": {"code": "EACCES", "message": "Permission denied"}
  }
}
```

**Output (`msg.topic`):**
```
v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged
```

### Field Mapping: FM2 → FASC

| FM2 Field | FASC Location | Type | Notes |
|-----------|---------------|------|-------|
| (entire) | `data` | Object | Complete source preserved |
| N/A | `specversion` | String | "1.0" (fixed) |
| N/A | `type` | String | "imec.event.file_action_status_changed" (fixed) |
| N/A | `source` | String | "urn:imec:ot:artemis:file-transfer-server" (fixed) |
| N/A | `subject` | String | Standard FASC topic path (fixed) |
| N/A | `id` | String | Generated UUID (unique per message) |
| N/A | `time` | String | ISO 8601 timestamp (when created) |
| N/A | `datacontenttype` | String | "application/json" (fixed) |
| N/A | `dataschema` | String | Schema URL (fixed) |

### Target File Reference
- **Path:** `ExampleMessages/DestinationMessages/FASC_260819.json`
- **Format:** CloudEvents v1.0
- **Schema:** IMEC File Action Status Changed Event

### Error Handling

| Scenario | Result | Output |
|----------|--------|--------|
| Valid `msg.parsedBody` | ✅ CloudEvent created | JSON string |
| Missing `msg.parsedBody` | ❌ Error | `msg.topic` undefined |
| Invalid data | ❌ Error | Exception thrown |

### Debug Output
```
🟢 CloudEvent created successfully
or
🔴 Error creating CloudEvent: [error message]
```

---

## Node 4: Store & Forward (Function) [PRODUCTION]

### Purpose
Queue messages during MQTT disconnection. When the "gate" is open, messages pass through. When closed, they're queued (max 100). On reconnection, the entire queue is flushed.

### Input Contract

**Regular Messages:**
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `msg.payload` | String | setupCloudEvent | CloudEvent JSON |
| `msg.topic` | String | setupCloudEvent | MQTT topic |

**Control Messages:**
| Field | Value | Purpose |
|-------|-------|---------|
| `msg.topic` | "control" | Identifies as control message |
| `msg.payload` | "open" or "queue" | Open gate or close gate |

### Processing Rules

1. **Check message type:**
   - If `topic === "control"` → Handle control command
   - Otherwise → Handle regular message

2. **If Control Message:**
   - `payload === "open"` → Set gate = open, flush queue
   - `payload === "queue"` → Set gate = closed, start queuing

3. **If Regular Message:**
   - Gate open? → Pass through to next node
   - Gate closed? → Add to queue (max 100 messages)

### Output Contract

| Scenario | `msg.payload` | `msg.topic` | Notes |
|----------|---------------|-------------|-------|
| Gate open | CloudEvent JSON | MQTT topic | Passed through |
| Gate closed | CloudEvent JSON | MQTT topic | Queued, not sent |
| Flushing | CloudEvent JSON | MQTT topic | Each queued message sent |

### Queue Behavior

```
Queue State: []

Message 1 arrives, gate open
  → Pass through
  → Queue: []

Message 2 arrives, gate closed (MQTT disconnect)
  → Add to queue
  → Queue: [msg2]

Message 3 arrives, gate closed
  → Add to queue
  → Queue: [msg2, msg3]

Control: "open" arrives
  → Flush queue
  → Send msg2, msg3, then the control message
  → Queue: []
```

### Field Mapping

| Source | Target | Condition |
|--------|--------|-----------|
| `msg.payload` | Output payload | Gate open → pass through |
| `msg.topic` | Output topic | Gate open → pass through |
| `msg` | Queue array | Gate closed → store in memory |
| Queue | Output messages | Control "open" → flush all |

### Error Handling

| Scenario | Result |
|----------|--------|
| Queue exceeds 100 messages | Drop oldest message, log warning |
| Control message malformed | Ignore, continue |
| Gate toggle rapid fire | Use last command |

---

## Node 5: Rate Limit (Built-in)

### Purpose
Throttle message throughput to prevent broker overload.

### Configuration
- **Rate:** 10 messages/second
- **Action:** Drop excess

### Input/Output Contract

| Aspect | Value |
|--------|-------|
| Input | CloudEvent JSON (unchanged) |
| Output | CloudEvent JSON (unchanged) |
| Behavior | Allow up to 10 msgs/sec, drop others |

### Example
```
Messages arriving: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] in 1 second
Rate limit: 10 msgs/sec
Output: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  (drop 11, 12)
```

---

## Node 6: Status Check (Function) [PRODUCTION]

### Purpose
Monitor MQTT connection status and send control signals to Store & Forward.

### Input Contract

| Source | Field | Type | Description |
|--------|-------|------|-------------|
| MQTT Out | Status events | Object | Connection state changes |
| Timer | Heartbeat | Timer | Every 10 seconds |

### Processing Rules

1. **On connection success:** Send control message `{ topic: "control", payload: "open" }` to Store & Forward
2. **On connection failure:** Send `{ topic: "control", payload: "queue" }`
3. **On disconnect:** Send `{ topic: "control", payload: "queue" }`
4. **Every 10s heartbeat:** Check status, adjust gate

### Output Contract

| Event | Output Message |
|-------|----------------|
| MQTT connected | `{ topic: "control", payload: "open" }` |
| MQTT disconnected | `{ topic: "control", payload: "queue" }` |
| MQTT error | `{ topic: "control", payload: "queue" }` |

### Status State Machine

```
Initial: [DISCONNECTED] ──gate=queue──

MQTT connects
    ↓
[CONNECTED] ──gate=open──

MQTT fails/disconnect
    ↓
[DISCONNECTED] ──gate=queue──

User reconnects
    ↓
[CONNECTED] ──gate=open──
    ↓
Flush queue
```

---

## Node 7: MQTT Out (Artemis MQTT Publisher)

### Purpose
Publish CloudEvent messages to MQTT broker.

### Input Contract

| Field | Type | Source | Required |
|-------|------|--------|----------|
| `msg.payload` | String | Rate Limit | ✅ Yes |
| `msg.topic` | String | setupCloudEvent | ✅ Yes |

### Configuration

| Setting | Value |
|---------|-------|
| Broker | Artemis MQTT (localhost:1883) |
| QoS | 1 (at least once) |
| Retain | false |
| Username | admin |
| Password | admin |

### Output Contract

| Aspect | Value |
|--------|-------|
| Protocol | MQTT v3.1.1 |
| Topic | `v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged` |
| Payload | CloudEvent v1.0 JSON string |
| QoS | 1 (broker guarantees delivery) |

### Example Publication

**Topic:**
```
v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged
```

**Payload:**
```json
{
  "specversion": "1.0",
  "type": "imec.event.file_action_status_changed",
  "source": "urn:imec:ot:artemis:file-transfer-server",
  "subject": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged",
  "id": "a1b2c3d4-e5f6-4789-ab00-123456789abc",
  "time": "2024-08-21T10:30:45.123Z",
  "datacontenttype": "application/json",
  "dataschema": "https://schemas.imec.be/imec.event.file_action_status_changed.v1.json",
  "data": { /* FM2 data */ }
}
```

---

## Complete End-to-End Example

### 1. Message Arrives at AMQP In

```json
{
  "durable": true,
  "priority": 4,
  "to": "IMEC.LEUVEN.FAB2.Development.FileManager.Server.Event.StatusUpdate",
  "body": "{\"header\":{\"correlationSystem\":\"CIRCL_2\",\"status\":\"ERROR\"}}"
}
```

### 2. After prepareBody

```json
{
  "parsedBody": {
    "header": {"correlationSystem": "CIRCL_2"},
    "status": "ERROR"
  },
  "payload": {
    "body": {
      "header": {"correlationSystem": "CIRCL_2"},
      "status": "ERROR"
    }
  },
  "rawBody": "{...original...}",
  "bodyParsed": true
}
```

### 3. After setupCloudEvent

```json
{
  "payload": "{\"specversion\":\"1.0\",\"type\":\"imec.event.file_action_status_changed\",...,\"data\":{\"header\":{\"correlationSystem\":\"CIRCL_2\"},\"status\":\"ERROR\"}}",
  "topic": "v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged"
}
```

### 4. After Store & Forward (gate open)

Same as setupCloudEvent output (passed through)

### 5. After Rate Limit

Same (within rate limit)

### 6. Published to MQTT

**Topic:** `v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged`  
**Payload:** CloudEvent JSON  
**QoS:** 1  

---

## Data Flow Summary

| Node | Input | Output | Transformation |
|------|-------|--------|-----------------|
| **AMQP In** | Raw AMQP msg | `msg.payload` (FM2) | No transform, receive only |
| **prepareBody** | `msg.payload.body` (string) | `msg.parsedBody` (object) | Recursive JSON.parse() |
| **setupCloudEvent** | `msg.parsedBody` (object) | `msg.payload` (CloudEvent string) | Wrap in v1.0 envelope + metadata |
| **StoreForward** | CloudEvent | Same (pass or queue) | Queue if disconnected, pass if connected |
| **RateLimit** | CloudEvent | Same | Throttle to 10 msgs/sec |
| **StatusCheck** | MQTT status | Control signals | Monitor → control gate |
| **MQTT Out** | CloudEvent + topic | MQTT publish | Protocol conversion + publish |

---

## Error Handling Strategy

| Node | Error | Action | Recovery |
|------|-------|--------|----------|
| prepareBody | Invalid JSON | Log error, set `bodyParsed=false` | Message discarded by downstream |
| setupCloudEvent | Missing data | Log error | Message discarded |
| StoreForward | Queue full | Drop oldest, log warning | Continue with new message |
| MQTT Out | Connection failed | StatusCheck sends "queue" | Store & Forward queues messages |
| MQTT Out | Publish fails | Retry (built-in) | QoS=1 guarantees attempt |

---

## Testing Checklist

- ✅ Input message has valid JSON in `body` field
- ✅ prepareBody successfully parses nested strings
- ✅ setupCloudEvent generates valid CloudEvent with UUID
- ✅ StoreForward opens gate when MQTT connects
- ✅ Rate Limit doesn't drop normal-speed messages
- ✅ MQTT Out publishes to correct topic
- ✅ Subscriber receives CloudEvent on MQTT topic
- ✅ Queue flushes when MQTT reconnects

---

## File References

| Document | Purpose |
|----------|---------|
| `ExampleMessages/SourceMessages/FM2/v260819` | Input example (FM2 format) |
| `ExampleMessages/DestinationMessages/FASC_260819.json` | Output example (CloudEvent format) |
| `NodeRedScripts/prepareBody.js` | Body parsing implementation |
| `NodeRedScripts/setupCloudEvent.js` | CloudEvent creation implementation |
| `NodeRedScripts/StoreForward.js` | Queueing logic implementation |
| `NodeRedScripts/StatusCheck.js` | Connection monitoring implementation |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-21 | 1.0 | Initial contract specification |

---

## Contact & Questions

For questions about data contracts:
1. Check this document for the node and field in question
2. Review example files in `ExampleMessages/`
3. Check the corresponding function node code in `NodeRedScripts/`
