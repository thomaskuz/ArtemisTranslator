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

## Alternate Flow: setupAmqpProperties.js — Header-in-Payload → Header-in-Header (AMQP → AMQP)

### Purpose
Deviation from Node 3 (`setupCloudEvent.js`) for a pure **AMQP → AMQP republish** flow — no CloudEvent envelope, no MQTT. Reuses `prepareBody.js` (Node 2) unchanged as its input stage. Named "header-in-payload → header-in-header" because the source message's `header` object — which arrives nested inside the AMQP payload's body — is promoted to a real AMQP `application_properties` header field, **while also staying in place inside the body** as its own `header` key. The same header data ends up addressable both ways: as broker-level AMQP properties (filterable via selectors) and embedded in the payload body (for consumers that read metadata from the body instead).

```
AMQP In  →  prepareBody.js  →  setupAmqpProperties.js  →  amqp-send
(FM2)        (Parse JSON)      (header → application_properties,
                                 header stays in body too)
```

### Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `msg.parsedBody` | Object | ✅ Yes | From `prepareBody.js` (Node 2), unchanged |
| `msg.parsedBody.header` | Object | ❌ No | Any shape — field-agnostic, no hardcoded key names |

### Processing Rules

1. **Validate:** Check `msg.parsedBody` exists
2. **Promote header → application properties:** Copy every key in `msg.parsedBody.header` into a new `application_properties` object (non-scalar values are JSON-stringified)
3. **Lift correlation id:** Search `header`'s keys case/separator-insensitively for a correlation-id-like field (matches `correlationId`, `correlationID`, `correlation_id`, `Correlation-Id`, ...) and set it as the standard AMQP `correlation_id` property too
4. **Build body:** `header` stays inside the body by default (`KEEP_HEADER_IN_BODY = true`) — same data as `application_properties`, just also embedded in the payload
5. **Wrap for amqp-send:** `node-red-contrib-rhea`'s `amqp-send` node reads the whole AMQP message as one object on `msg.payload` — `body`, `application_properties`, `correlation_id`, `content_type` as sibling keys (confirmed against the Artemis console; see `guides/amqp-message-fields-nodered.md`)
6. **Clean up:** Drop `msg.rawBody` / `msg.parsedBody` / `msg.bodyParsed` — their data now lives in `msg.payload`

### Output Contract

| Field | Type | Description |
|-------|------|--------------|
| `msg.payload.body` | Object | The full parsed body, `header` included |
| `msg.payload.application_properties` | Object | Same fields as `body.header`, promoted to AMQP application properties |
| `msg.payload.correlation_id` | String | Only set if a correlation-id-like field was found in `header` |
| `msg.payload.content_type` | String | `"application/json"` |

### Example Transformation

**Input (`msg.parsedBody`):**
```json
{
  "header": {
    "correlationSystem": "CIRCL_2",
    "correlationId": "62",
    "publisherSystem": "FILEMANAGER01",
    "messageType": "FileManagerRequestStatusUpdateMessage",
    "messageVersion": "0.2.0"
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
  "body": {
    "header": {
      "correlationSystem": "CIRCL_2",
      "correlationId": "62",
      "publisherSystem": "FILEMANAGER01",
      "messageType": "FileManagerRequestStatusUpdateMessage",
      "messageVersion": "0.2.0"
    },
    "status": "ERROR",
    "error": { "code": "EACCES", "message": "Permission denied" }
  },
  "application_properties": {
    "correlationSystem": "CIRCL_2",
    "correlationId": "62",
    "publisherSystem": "FILEMANAGER01",
    "messageType": "FileManagerRequestStatusUpdateMessage",
    "messageVersion": "0.2.0"
  },
  "correlation_id": "62",
  "content_type": "application/json"
}
```

### Field Mapping: Header-in-Payload → Header-in-Header

| Source | Target | Transformation |
|--------|--------|-----------------|
| `msg.parsedBody.header.*` | `msg.payload.application_properties.*` | Copied field-agnostic, non-scalars stringified |
| `msg.parsedBody.header.*` | `msg.payload.body.header.*` | Unchanged, stays in place (not moved, not removed) |
| `msg.parsedBody.header.<correlation-id-like key>` | `msg.payload.correlation_id` | Regex-matched key, promoted to standard AMQP property |
| `msg.parsedBody` (minus none — header stays) | `msg.payload.body` | Passed through as-is |

### Confirmed Working

Verified against the live Artemis broker (console message view): `applicationProperties.*` entries populate correctly for every `header` field, and `properties.correlationId` / `properties.contentType` show the promoted values — this required the exact nesting shown above (everything inside `msg.payload`), not a flat `msg.applicationProperties`/`msg.correlation_id`.

### Related Files
- Implementation: `NodeRedScripts/setupAmqpProperties.js`
- Reverse flow (application_properties → header, for received messages): `NodeRedScripts/copyPropertiesToHeader.js`
- Field mapping reference: `guides/amqp-message-fields-nodered.md`

---

## Alternate Flow: copyPropertiesToHeader.js — Header-in-Header → Header-in-Payload (AMQP → AMQP)

### Purpose
Reverse of the flow above. Takes an AMQP message straight from `amqp-recv` — where the metadata already lives purely as broker-level AMQP `application_properties` ("header-in-header": a header that exists only as an AMQP header/property, not embedded anywhere in the payload) — and copies it into a `header` object placed **inside the body**, so the same data also becomes part of the payload ("header-in-payload"). Republishes via `amqp-send`.

```
amqp-recv  →  copyPropertiesToHeader.js  →  amqp-send
(application_properties    (application_properties → body.header,
 only, no header in body)   application_properties also carried through)
```

### Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `msg.payload.application_properties` | Object | ❌ No | Flat key/value, as delivered by `amqp-recv` |
| `msg.payload.body` | Object or String | ❌ No | The message body — parsed if it's a JSON string |
| `msg.payload.correlation_id` | String | ❌ No | Added to `header` only if no `application_properties` field already looks like a correlation id |

### Processing Rules

1. **Normalize body:** Accept `msg.payload.body` as object or JSON string; parse strings, fall back to `{ data: body }` if not valid JSON
2. **Copy application properties → header:** Field-agnostic — copies whatever keys `application_properties` has, no hardcoded names
3. **Lift correlation id:** If `msg.payload.correlation_id` is set and no `application_properties` field already matches a correlation-id pattern (case/separator-insensitive), add it into `header` as `correlationId`
4. **Embed header in body:** Set `body.header = header`
5. **Wrap for amqp-send:** Rebuild `msg.payload` with `body` and `application_properties` (carried through unchanged) as sibling keys, plus `correlation_id`/`content_type` if present on the incoming message — same contract `amqp-send` requires (see `guides/amqp-message-fields-nodered.md`)
6. **Clean up:** Drop `msg.rawBody` / `msg.parsedBody` / `msg.bodyParsed` if present from an upstream `prepareBody.js`

### Output Contract

| Field | Type | Description |
|-------|------|--------------|
| `msg.payload.body.header` | Object | Same fields as `application_properties`, now embedded in the body |
| `msg.payload.application_properties` | Object | Carried through unchanged, for `amqp-send` |
| `msg.payload.correlation_id` | String | Carried over, if present on the incoming message |
| `msg.payload.content_type` | String | Carried over, if present on the incoming message |

### Example Transformation

**Input (`msg.payload`, as delivered by `amqp-recv`):**
```json
{
  "application_properties": {
    "correlationSystem": "CIRCL_2",
    "correlationId": 62,
    "publisherSystem": "FILEMANAGER01",
    "messageType": "FileManagerRequestStatusUpdateMessage",
    "messageVersion": "0.2.0"
  },
  "correlation_id": "62",
  "content_type": "application/json",
  "body": {
    "schemaVersion": "0.2.0",
    "statusUpdateId": "af9070b2-ff63-4187-a2b5-f0b3fda793a8",
    "status": "ERROR"
  }
}
```

**Output (`msg.payload`):**
```json
{
  "body": {
    "schemaVersion": "0.2.0",
    "statusUpdateId": "af9070b2-ff63-4187-a2b5-f0b3fda793a8",
    "status": "ERROR",
    "header": {
      "correlationSystem": "CIRCL_2",
      "correlationId": 62,
      "publisherSystem": "FILEMANAGER01",
      "messageType": "FileManagerRequestStatusUpdateMessage",
      "messageVersion": "0.2.0"
    }
  },
  "application_properties": {
    "correlationSystem": "CIRCL_2",
    "correlationId": 62,
    "publisherSystem": "FILEMANAGER01",
    "messageType": "FileManagerRequestStatusUpdateMessage",
    "messageVersion": "0.2.0"
  },
  "correlation_id": "62",
  "content_type": "application/json"
}
```

### Field Mapping: Header-in-Header → Header-in-Payload

| Source | Target | Transformation |
|--------|--------|-----------------|
| `msg.payload.application_properties.*` | `msg.payload.body.header.*` | Copied field-agnostic, no hardcoded keys |
| `msg.payload.application_properties.*` | `msg.payload.application_properties.*` | Carried through unchanged (not moved, not removed) |
| `msg.payload.correlation_id` | `msg.payload.body.header.correlationId` | Only added if no `application_properties` field already matches a correlation-id pattern |
| `msg.payload.correlation_id` / `content_type` | Same, top-level `msg.payload` | Carried through unchanged, if present |

### Confirmed Working

Verified against the live Artemis broker the same way as `setupAmqpProperties.js`: `body`/`application_properties` must be nested inside `msg.payload` as sibling keys for `amqp-send` to actually publish them — an earlier flattened attempt (data split across `msg.applicationProperties` and a flattened `msg.payload`) produced a null body and no `applicationProperties.*` entries on the broker.

### Related Files
- Implementation: `NodeRedScripts/copyPropertiesToHeader.js`
- Debug/test injector (simulates `amqp-recv` output): `NodeRedScripts/debugInjectAmqpProperties.js`
- Forward flow (header → application_properties, for outbound messages): `NodeRedScripts/setupAmqpProperties.js`
- Field mapping reference: `guides/amqp-message-fields-nodered.md`

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

## Alternate Flow: mesAmqpToMqttPublisher.js — MES AMQP → MQTT (E3 Integration)

### Purpose
A separate pipeline from the main FASC flow above — transforms a real incoming AMQP message into the MES TrackIn CloudEvent + MQTT v5 property shape E3 requires. Production replacement for the older `mesMQTTPublisher.js`, which fabricated all its data from a hardcoded demo payload (see that node's entry below for what was hardcoded vs. what's genuinely required by E3).

```
amqp-recv → mesAmqpToMqttPublisher.js → MQTT Out (v5)
```

Single self-contained Function node — unlike the main pipeline, there's no separate "parse" step feeding into it, since `amqp-recv`'s output shape is simple enough to normalize inline.

### Input Contract

| Field | Type | Required | Description |
|-------|------|----------|--------------|
| `msg.payload` | Object or String | ✅ Yes | From `amqp-recv` — normalized first: parsed if the whole message arrived as a stringified JSON blob |
| `msg.payload.application_properties` | Object | ❌ No | Field-agnostic — whatever the source system set, defaults to `{}` |
| `msg.payload.correlation_id` | String | ❌ No | Real AMQP correlation-id; only promoted to `msg.correlationData` if present |
| `msg.payload.body` | Object or String | ❌ No | The actual MES data; normalized (parsed if a JSON string) before use |

### Processing Rules

1. **Normalize `msg.payload`** — parse if it's a string, so the rest of the function always has an object to work with
2. **Normalize `msg.payload.body`** — same treatment
3. **Build `mesPayload`** — same `{ "MES_Data": { ...CloudEvent envelope..., data: <body> } }` shape as `mesMQTTPublisher.js` used, but `data` is the real AMQP body, and `id`/`time` are freshly generated per message
4. **Set MQTT v5 predefined properties** — `contentType`, `correlationData` (from real `correlation_id`, guarded), `messageExpiryInterval`, `payloadFormatIndicator`
5. **Build `userProperties`** — spread `application_properties` first (field-agnostic), then the four static E3-required properties last, so they win on any key collision

### Output Contract

| Field | Type | Description |
|-------|------|--------------|
| `msg.payload` | Object | `mesPayload` — the `MES_Data` CloudEvent wrapper, real body as `data` |
| `msg.topic` | String | `"fromAppToE3"` |
| `msg.contentType` | String | `"application/json"` |
| `msg.correlationData` | String | From `msg.payload.correlation_id`, only if present |
| `msg.messageExpiryInterval` | Number | `3600` (seconds) |
| `msg.payloadFormatIndicator` | Number | `1` (UTF-8 text) |
| `msg.userProperties` | Object | AMQP `application_properties` merged with the 4 static E3-required properties |

### Confirmed E3-Required Fields (validated against real E3 rejections during earlier development)

| Field | Value | Why |
|---|---|---|
| `msg.topic` | `"fromAppToE3"` | E3's actual subscription topic |
| `msg.contentType` | `"application/json"` | E3 explicitly checks this |
| `msg.correlationData` | unique ID | E3 requires it present |
| `userProperties["action-name"]` | `"TRACKIN"` | Event type routing |
| `userProperties["application-name"]` | `"E3_MES_Integration"` | **Underscores, not spaces** — literal cause of an earlier E3 rejection bug |
| `userProperties["source"]` | `"MES"` | Origin identification |
| `userProperties["status"]` | `"200"` | E3-expected status convention |

### Related Files
- Implementation: `NodeRedScripts/mesAmqpToMqttPublisher.js`
- Superseded demo version: `NodeRedScripts/mesMQTTPublisher.js`
- Setup guide: `guides/nodered-mes-mqtt-publisher.md`

---

## Node 8: mesMQTTPublisher.js (Function) — Superseded Demo Version

### Purpose
Standalone test/demo publisher — **not fed by AMQP at all**, triggered manually by an Inject node. Generates a fully hardcoded MES TrackIn CloudEvent on every trigger. Historically useful for validating the E3 property contract in isolation before a real AMQP source existed; superseded by `mesAmqpToMqttPublisher.js` above once verified against real traffic.

```
Inject → mesMQTTPublisher.js → MQTT Out (v5)
```

### Input Contract

| Field | Required? | Notes |
|---|---|---|
| *(none)* | — | Reads nothing off the incoming `msg` — pure generator, not a transformer |

### What's Hardcoded vs. Genuinely Required

Only a subset of the hardcoded fields are actually necessary; the rest is fabricated demo business data:

| Category | Fields | Notes |
|---|---|---|
| **E3-required** (see table above) | `topic`, `contentType`, `correlationData`, all 4 `userProperties` | Confirmed via real E3 rejections |
| **CloudEvents/schema convention** | `specversion`, `datacontenttype`, `type`, `dataschema`, `data.schemaVersion`, `data.eventType`, `data.sourceSystem` | Fixed per event type, not individually verified against E3 but shouldn't change without reason |
| **Pure demo filler** | `data.sourceCorrelationId`, `toolName`, `carrierId`, `lotName`, `product`, `flowName`, `flowRecipe`, `substrates`, etc. | Arbitrary fabricated values — `sourceCorrelationId` is the clearest example, a hardcoded static UUID that should vary per real transaction |

### Output Contract

Same shape as `mesAmqpToMqttPublisher.js`'s output (see above), except `msg.payload.MES_Data.data` is always the same fabricated demo content rather than real AMQP data, and `msg.payload` is **not** stringified (relies on MQTT Out's implicit object-to-JSON auto-conversion, unlike `setupCloudEvent.js` which stringifies explicitly).

### Related Files
- Implementation: `NodeRedScripts/mesMQTTPublisher.js`
- Production replacement: `NodeRedScripts/mesAmqpToMqttPublisher.js`
- Setup guide: `guides/nodered-mes-mqtt-publisher.md`

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
| `ExampleMessages/SourceMessages/FM2/AMQPNR_v260819` | Real captured amqp-recv output (node-red-contrib-rhea shape) |
| `ExampleMessages/DestinationMessages/FASC_260819.json` | Output example (CloudEvent format) |
| `ExampleMessages/DestinationMessages/MES_TrackIn_v1.json` | Output example (MES TrackIn CloudEvent format) |
| `NodeRedScripts/prepareBody.js` | Body parsing implementation |
| `NodeRedScripts/setupCloudEvent.js` | CloudEvent creation implementation |
| `NodeRedScripts/StoreForward.js` | Queueing logic implementation |
| `NodeRedScripts/StatusCheck.js` | Connection monitoring implementation |
| `NodeRedScripts/setupAmqpProperties.js` | AMQP-only republish: header → application_properties |
| `NodeRedScripts/copyPropertiesToHeader.js` | AMQP-only republish: application_properties → header (reverse) |
| `NodeRedScripts/debugInjectAmqpProperties.js` | Test injector for the reverse AMQP flow |
| `NodeRedScripts/mesAmqpToMqttPublisher.js` | MES AMQP → MQTT, production (real data) |
| `NodeRedScripts/mesMQTTPublisher.js` | MES AMQP → MQTT, superseded demo (hardcoded data) |
| `guides/amqp-message-fields-nodered.md` | AMQP/MQTT field mapping reference, confirmed against the live broker |
| `guides/nodered-mes-mqtt-publisher.md` | MES → E3 flow setup guide |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-21 | 1.0 | Initial contract specification |
| 2026-09-18 | 1.1 | Added alternate flows: setupAmqpProperties.js / copyPropertiesToHeader.js (AMQP-only republish, header-in-payload ↔ header-in-header), mesAmqpToMqttPublisher.js (production MES→E3 replacing hardcoded mesMQTTPublisher.js). Documented confirmed node-red-contrib-rhea msg.payload nesting contract. |

---

## Contact & Questions

For questions about data contracts:
1. Check this document for the node and field in question
2. Review example files in `ExampleMessages/`
3. Check the corresponding function node code in `NodeRedScripts/`
