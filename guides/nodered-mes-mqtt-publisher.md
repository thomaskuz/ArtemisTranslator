# NodeRed MES MQTT Publisher Guide

NodeRed flows to publish MES TrackIn events with proper MQTT v5 metadata to the E3 system. Two versions exist:

- **`mesAmqpToMqttPublisher.js`** (recommended) — sources real data from an incoming AMQP message
- **`mesMQTTPublisher.js`** (demo/testing) — fabricates a fixed demo payload on manual trigger, no AMQP source needed

Use the demo version for isolated testing of the E3 property contract without a live AMQP source; use the production version once you have a real AMQP message stream to transform.

---

## Production Flow: mesAmqpToMqttPublisher.js

### Flow Architecture

```
[amqp-recv] → [MES AMQP-to-MQTT Publisher Function] → [MQTT Out]
              (transforms real AMQP message)           (publishes)
```

### Setup

#### Step 1: Create `amqp-recv` Node (node-red-contrib-rhea)

1. Drag **amqp-recv** node to canvas
2. Configure broker connection: `localhost:5672`, credentials `admin`/`admin`
3. Set the source **address** (or `address::queue` — see `guides/amqp-multicast-anycast-behavior.md` for the distinction) carrying the real MES-related AMQP messages

#### Step 2: Create Function Node (MES Publisher)

1. Drag **Function** node to canvas
2. Connect: **amqp-recv** → **Function**
3. Paste entire code from `NodeRedScripts/mesAmqpToMqttPublisher.js`
4. **Name:** "MES AMQP-to-MQTT Publisher"

#### Step 3: Create MQTT Out Node (Publish)

Same as the demo flow below — **Broker:** `localhost:1883`, **Username/Password:** `admin`/`admin`, **protocol version 5**, **Topic:** leave blank (function sets `msg.topic`), **QoS:** `1` recommended.

#### Step 4: Deploy and Test

1. Deploy the flow
2. Send/receive a real AMQP message on the configured address
3. Verify the transformed message reaches `fromAppToE3` — see Testing section below

### What the Function Does

- **Normalizes `msg.payload`** — handles both object and stringified-JSON forms from `amqp-recv` (see `DataContracts.md` for the full input contract)
- **Wraps the real AMQP body** in the same `MES_Data` CloudEvent envelope the demo version used, but `data` is the actual message content instead of fabricated fields
- **Promotes AMQP `application_properties` → MQTT `userProperties`**, field-agnostic
- **Promotes AMQP `correlation_id` → MQTT `correlationData`**
- **Merges in the 4 static E3-required properties** (see below) — added last, so they win on any key collision with the real AMQP properties

### Input/Output Contracts

Full data models, requirements, and step-by-step traces (including a worked example against `ExampleMessages/SourceMessages/FM2/AMQPNR_v260819`): see `DataContracts.md` → "Alternate Flow: mesAmqpToMqttPublisher.js".

---

## Demo/Testing Flow: mesMQTTPublisher.js

### Flow Architecture

```
[Inject] → [MES MQTT Publisher Function] → [MQTT Out]
            (Creates fixed demo payload)    (Publishes)
```

No AMQP source needed — useful for testing the E3 property contract in isolation.

### Setup

#### Step 1: Create Inject Node (Trigger)

1. Drag **Inject** node to canvas
2. Double-click to configure:
   - **Name:** "Trigger MES Event"
   - **Payload:** Leave default (timestamp)
3. Click **Done**

#### Step 2: Create Function Node (MES Publisher)

1. Drag **Function** node to canvas
2. Connect: **Inject** → **Function**
3. Double-click and paste entire code from `NodeRedScripts/mesMQTTPublisher.js`
4. **Name:** "MES MQTT Publisher"
5. Click **Done**

#### Step 3: Create MQTT Out Node (Publish)

1. Drag **MQTT Out** node to canvas
2. Connect: **Function** → **MQTT Out**
3. Double-click to configure:
   - **Broker:** `localhost:1883` (or configure new)
   - **Username:** `admin`
   - **Password:** `admin`
   - **Protocol Version:** `5` (MQTT v5 — required for `contentType`/`correlationData`/`userProperties` to actually transmit)
   - **Topic:** leave blank (function sets `msg.topic`)
   - **QoS:** `0` or `1`
   - **Retain:** `false`
4. Click **Done**

#### Step 4: Deploy and Test

1. Click **Deploy** (red button, top right)
2. Click the **Inject** node to trigger
3. Message publishes to Artemis MQTT
4. Check in **Artemis Console** or **MQTT subscriber** for message

---

## Complete Flow Code (Copy-Paste) — Demo Version

If you want to import the demo flow directly:

```json
[
  {
    "id": "inject_mes",
    "type": "inject",
    "z": "flow_id",
    "name": "Trigger MES Event",
    "props": [
      {"p": "payload"},
      {"p": "topic", "vt": "str"}
    ],
    "repeat": "",
    "crontab": "",
    "once": false,
    "onceDelay": 0.1,
    "topic": "",
    "payload": "",
    "payloadType": "date",
    "x": 100,
    "y": 100,
    "wires": [["function_mes"]]
  },
  {
    "id": "function_mes",
    "type": "function",
    "z": "flow_id",
    "name": "MES MQTT Publisher",
    "func": "// [Copy entire function code from mesMQTTPublisher.js here]",
    "outputs": 1,
    "noerr": 0,
    "initialize": "",
    "finalize": "",
    "libs": [],
    "x": 280,
    "y": 100,
    "wires": [["mqtt_out"]]
  },
  {
    "id": "mqtt_out",
    "type": "mqtt out",
    "z": "flow_id",
    "name": "MQTT Out",
    "topic": "fromAppToE3",
    "qos": "0",
    "retain": "false",
    "broker": "mqtt_broker_id",
    "x": 460,
    "y": 100,
    "wires": []
  },
  {
    "id": "mqtt_broker_id",
    "type": "mqtt-broker",
    "name": "Artemis MQTT",
    "broker": "localhost",
    "port": "1883",
    "clientid": "nodered-mes-publisher",
    "autoConnect": true,
    "usetls": false,
    "protocolVersion": "5",
    "keepalive": "60",
    "cleansession": true,
    "birthTopic": "",
    "birthQos": "0",
    "birthPayload": "",
    "birthMsg": false,
    "closeTopic": "",
    "closeQos": "0",
    "closePayload": "",
    "closeMsg": false,
    "willTopic": "",
    "willQos": "0",
    "willPayload": "",
    "willMsg": false,
    "sessionExpiry": ""
  }
]
```

---

## What the Demo Function Does

### Creates MES Payload (fixed demo data)
```javascript
msg.payload = {
  "MES_Data": {
    "specversion": "1.0",
    "type": "imec.mes.trackin",
    "...": "...",
    "data": { /* Fixed demo MES TrackIn data - toolName, lotName, etc. */ }
  }
}
```

### Sets MQTT Topic
```javascript
msg.topic = "fromAppToE3"
```

### Sets MQTT v5 Predefined Properties
```javascript
msg.contentType = "application/json";           // ← Required by E3
msg.correlationData = msgId;                     // ← Required by E3 (unique ID)
msg.messageExpiryInterval = 3600;
msg.payloadFormatIndicator = 1;
```

### Sets User Properties (Custom Metadata)
```javascript
msg.userProperties = {
  "action-name": "TRACKIN",
  "application-name": "E3_MES_Integration",   // ← Note: underscores, not spaces!
  "source": "MES",
  "status": "200"
};
```

**Note:** predefined properties (`contentType`, `correlationData`, etc.) and custom `userProperties` are two **separate** `msg` fields, not one combined object — this is how MQTT v5 itself distinguishes them on the wire. See `guides/amqp-message-fields-nodered.md` for the full property-type breakdown.

**Required by E3:**
- `msg.contentType` — must be `application/json`
- `msg.correlationData` — unique message ID for tracking

**Custom properties (`userProperties`):**
- `action-name`: Type of action (TRACKIN)
- `application-name`: **E3_MES_Integration** (with underscores!)
- `source`: Identifies as coming from MES
- `status`: HTTP-like status code

---

## Customization (Demo Version Only)

The demo version's data is fully hardcoded — customize it directly in the function:

### Change Tool Name
```javascript
"toolName": "YOUR_TOOL_NAME",
```

### Change Lot Name
```javascript
"lotName": "LOT" + new Date().toISOString().split('T')[0].replace(/-/g, '') + "001",
```

### Change Carrier ID
```javascript
"carrierId": "YOUR_CARRIER_ID",
```

### Change Product
```javascript
"product": "YOUR_PRODUCT",
"productType": "Production",  // or "Test"
```

### Change Wafer Count
Modify the `slotMapContent` array and `substrates` array (each has 25 slots by default).

For the **production version**, customization isn't needed here — the actual data comes from the real AMQP message instead.

---

## Testing with MQTT Subscriber

While either flow is running, in another terminal:
```bash
python scripts/mqtt_subscriber.py
```

You should see MES TrackIn messages published to the `fromAppToE3` topic, including the `Properties (MQTT Metadata)` block showing `userProperties` and predefined properties.

---

## Integration with E3

The E3 system reads:
- **Topic:** `fromAppToE3` (routing)
- **Properties:** `action-name`, `application-name`, `source`, `status` (via `userProperties`), plus `contentType`/`correlationData` (predefined properties)
- **Payload:** `MES_Data` JSON with complete event information

E3 uses the `source: "MES"` property to identify this came from the MES system.

---

## Related Files

- Production implementation: `NodeRedScripts/mesAmqpToMqttPublisher.js`
- Demo/testing implementation: `NodeRedScripts/mesMQTTPublisher.js`
- Full input/output contracts: `DataContracts.md`
- AMQP/MQTT field mapping reference: `guides/amqp-message-fields-nodered.md`
- Example payload: `ExampleMessages/DestinationMessages/MES_TrackIn_v1.json`
- Real captured AMQP input example: `ExampleMessages/SourceMessages/FM2/AMQPNR_v260819`

---

## Troubleshooting

### Message not publishing
- ✅ Check MQTT broker connection (yellow indicator)
- ✅ Verify credentials: `admin:admin`
- ✅ Check topic name matches E3 expectation
- ✅ Confirm MQTT Out node is set to **protocol version 5** — v3.1.1 silently drops `contentType`/`correlationData`/`userProperties`

### E3 not receiving messages
- ✅ Verify `source` property is set to `"MES"`
- ✅ Check topic is `"fromAppToE3"`
- ✅ Verify `application-name` uses underscores, not spaces
- ✅ Verify payload format matches schema

### Production flow: userProperties/correlationData missing
- ✅ Confirm the upstream AMQP message actually has `application_properties`/`correlation_id` set — `mesAmqpToMqttPublisher.js` only promotes what's present, it doesn't fabricate them
- ✅ Check `amqp-recv`'s output shape in a Debug node against the input contract in `DataContracts.md`

### Function has syntax errors
- ✅ Copy the entire code from the relevant script file
- ✅ Check for missing quotes or brackets
- ✅ Validate JSON structure in payload
