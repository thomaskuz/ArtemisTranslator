# NodeRed MES MQTT Publisher Guide

Simple NodeRed flow to publish MES TrackIn events with proper MQTT metadata to E3 system.

## Flow Architecture

```
[Inject] → [MES MQTT Publisher Function] → [MQTT Out]
            (Creates payload + properties)   (Publishes)
```

## Setup

### Step 1: Create Inject Node (Trigger)

1. Drag **Inject** node to canvas
2. Double-click to configure:
   - **Name:** "Trigger MES Event"
   - **Payload:** Leave default (timestamp)
3. Click **Done**

### Step 2: Create Function Node (MES Publisher)

1. Drag **Function** node to canvas
2. Connect: **Inject** → **Function**
3. Double-click and paste entire code from `NodeRedScripts/mesMQTTPublisher.js`
4. **Name:** "MES MQTT Publisher"
5. Click **Done**

### Step 3: Create MQTT Out Node (Publish)

1. Drag **MQTT Out** node to canvas
2. Connect: **Function** → **MQTT Out**
3. Double-click to configure:
   - **Broker:** `localhost:1883` (or configure new)
   - **Username:** `admin`
   - **Password:** `admin`
   - **Topic:** `fromAppToE3` (or leave blank to use msg.topic from function)
   - **QoS:** `0` (fire-and-forget)
   - **Retain:** `false`
4. Click **Done**

### Step 4: Deploy and Test

1. Click **Deploy** (red button, top right)
2. Click the **Inject** node to trigger
3. Message publishes to Artemis MQTT
4. Check in **Artemis Console** or **MQTT subscriber** for message

---

## Complete Flow Code (Copy-Paste)

If you want to import the flow directly:

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
    "protocolVersion": "4",
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

## What the Function Does

### Creates MES Payload
```javascript
msg.payload = {
  "MES_Data": {
    "specversion": "1.0",
    "type": "imec.mes.trackin",
    ...
    "data": { /* Full MES TrackIn data */ }
  }
}
```

### Sets MQTT Topic
```javascript
msg.topic = "fromAppToE3"  // Topic for MQTT publish
```

### Sets User Properties (Metadata)
```javascript
msg.properties = {
  "Content-Type": "application/json",      // ← Required by E3
  "Correlation-Data": msgId,                // ← Required by E3 (unique ID)
  "action-name": "TRACKIN",
  "application-name": "E3_MES_Integration", // ← Note: underscores, not spaces!
  "source": "MES",
  "status": "200"
}
```

**Required by E3:**
- `Content-Type`: Must be `application/json`
- `Correlation-Data`: Unique message ID for tracking

**Custom properties:**
- `action-name`: Type of action (TRACKIN)
- `application-name`: **E3_MES_Integration** (with underscores!)
- `source`: Identifies as coming from MES
- `status`: HTTP-like status code

---

## Customization

### Change Tool Name
Edit in function:
```javascript
"toolName": "YOUR_TOOL_NAME",  // Change this
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

---

## Testing with MQTT Subscriber

While the flow is running, in another terminal:
```bash
python scripts/mqtt_subscriber.py
```

You should see MES TrackIn messages published to `fromAppToE3` topic.

---

## Integration with E3

The E3 system will read:
- **Topic:** `fromAppToE3` (routing)
- **Properties:** `action-name`, `application-name`, `source`, `status`
- **Payload:** MES_Data JSON with complete event information

E3 uses the `source: "MES"` property to identify this came from the MES system.

---

## Related Files

- Source code: `NodeRedScripts/mesMQTTPublisher.js`
- Example payload: `ExampleMessages/DestinationMessages/MES_TrackIn_v1.json`
- Full MQTT guide: `guides/nodered-mqtt-publisher.md`

---

## Troubleshooting

### Message not publishing
- ✅ Check MQTT broker connection (yellow indicator)
- ✅ Verify credentials: `admin:admin`
- ✅ Check topic name matches E3 expectation

### E3 not receiving messages
- ✅ Verify `source` property is set to `"MES"`
- ✅ Check topic is `"fromAppToE3"`
- ✅ Verify payload format matches schema

### Function has syntax errors
- ✅ Copy entire code from `mesMQTTPublisher.js`
- ✅ Check for missing quotes or brackets
- ✅ Validate JSON structure in payload
