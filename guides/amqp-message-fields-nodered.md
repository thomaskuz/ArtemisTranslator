# AMQP Message Fields — Practical Guide for NodeRed

How AMQP 1.0 message fields map to what you actually set in a NodeRed **Function** node, for both publishing paths we use: the **MQTT Out** node (bridged through Artemis) and the **amqp-send** node from `node-red-contrib-rhea`.

> **Confirmed against our own broker** (Artemis console message view): `amqp-send` reads the **entire** AMQP message as **one object on `msg.payload`** — `body`, `application_properties`, `correlation_id`, `content_type`, `durable`, `priority`, `ttl`, etc. all live as **sibling keys inside `msg.payload`**, not flat on `msg` itself. `amqp-recv` delivers received messages the same way, symmetrically. This is specific to `node-red-contrib-rhea` — a different AMQP NodeRed package may structure things differently, so re-verify against the broker if you switch packages.

## The Big Picture

An AMQP message is built from a few blocks, sent in a fixed order:

```
Header              → delivery behavior (durable, priority, ttl)
Message Annotations → broker/infra metadata (not yours to set)
Properties           → standard fields (content-type, correlation-id, subject...)
Application Properties → YOUR custom key/values (filterable, this is what E3 reads)
Body                 → the actual payload
```

MQTT v5 is flatter — no separate Header/Properties split, just one set of predefined properties plus your custom ones:

```
Predefined Properties → Content-Type, Correlation-Data, Message-Expiry-Interval, ...
User Properties        → YOUR custom key/values (filterable, this is what E3 reads)
Payload                 → the actual message content
```

**In NodeRed, you never build this by hand.** You set values on `msg.*` in a Function node, and the outbound node (MQTT Out or amqp-send) handles the wire framing. The tables below show, per field, whether it's settable, and the exact `msg.*` shape for **both** paths.

### Minimal Example Layout

**On the wire**, AMQP 1.0 really does group these into separate sections:

```json
{
  "header": {
    "durable": true,
    "priority": 4,
    "ttl": 300000
  },
  "properties": {
    "messageId": "msg-001",
    "correlationId": "msgId_182396143986",
    "contentType": "application/json"
  },
  "applicationProperties": {
    "action-name": "TRACKIN",
    "application-name": "E3_MES_Integration",
    "source": "MES",
    "status": "200"
  },
  "body": {
    "eventType": "TRACKIN",
    "lotName": "LOT20260702001"
  }
}
```

**But on `msg` in NodeRed** (`node-red-contrib-rhea`'s `amqp-send`/`amqp-recv`), everything — header fields, properties fields, application properties, and the body — is nested **inside `msg.payload`** as sibling keys. `msg` itself carries nothing AMQP-specific:

```json
{
  "payload": {
    "durable": true,
    "priority": 4,
    "ttl": 300000,
    "correlation_id": "msgId_182396143986",
    "content_type": "application/json",
    "application_properties": {
      "action-name": "TRACKIN",
      "application-name": "E3_MES_Integration",
      "source": "MES",
      "status": "200"
    },
    "body": {
      "eventType": "TRACKIN",
      "lotName": "LOT20260702001"
    }
  }
}
```

This is the shape you're recreating in a Function node — every AMQP field, `application_properties`, and `body` all live under `msg.payload`, not on `msg` directly.

### Minimal MQTT v5 Equivalent

MQTT v5 has **no `header` block**, and — unlike the AMQP Out node — its fields sit directly on **`msg`**, not nested under `msg.payload`. Only `userProperties` is a nested key/value object, and `msg.payload` holds *only* the body:

```json
{
  "topic": "fromAppToE3",
  "qos": 1,
  "retain": false,
  "contentType": "application/json",
  "correlationData": "msgId_182396143986",
  "messageExpiryInterval": 3600,
  "payloadFormatIndicator": 1,
  "userProperties": {
    "action-name": "TRACKIN",
    "application-name": "E3_MES_Integration",
    "source": "MES",
    "status": "200"
  },
  "payload": {
    "eventType": "TRACKIN",
    "lotName": "LOT20260702001"
  }
}
```

This is `msg` as set in the Function node feeding MQTT Out — no `properties`/`application_properties` split like AMQP, everything except `userProperties` and `payload` is a top-level field on `msg` itself. **This is the opposite nesting from the AMQP Out node** — worth double-checking which one you're editing.

---

## 1. Header Fields (delivery behavior)

### AMQP 1.0 — Header section

| Field | Customizable? | MQTT Out node | amqp-send node |
|---|---|---|---|
| `durable` | ✅ Yes | Set **QoS 1 or 2** on the MQTT Out node config (QoS 0 = non-durable) | `msg.payload.durable = true` |
| `priority` | ✅ Yes (AMQP only) | ❌ Not exposed by MQTT Out — skip for the E3/MQTT flow | `msg.payload.priority = 5` (0–9) |
| `ttl` | ✅ Yes | `msg.messageExpiryInterval = 3600` (seconds — MQTT v5 equivalent) | `msg.payload.ttl = 300000` (**milliseconds**, not seconds) |
| `delivery-count` | ❌ No, read-only | N/A — broker manages this | N/A — broker manages this, only visible on **received** messages (`msg.payload.delivery_count`) |

### MQTT v5 — Predefined PUBLISH Properties

This is the full list of predefined properties MQTT v5 allows on a PUBLISH packet — the closest equivalent to AMQP's Header + Properties sections combined:

| Property | Customizable? | Set where | How in NodeRed (MQTT Out) |
|---|---|---|---|
| Payload Format Indicator | ✅ Yes | Per-message | `msg.payloadFormatIndicator = 1` (0 = bytes, 1 = UTF-8 text) |
| Message Expiry Interval | ✅ Yes | Per-message | `msg.messageExpiryInterval = 3600` (**seconds**, not ms) |
| Topic Alias | ✅ Yes | Per-message | `msg.topicAlias = 1` — rarely needed, saves bandwidth on repeated topics |
| Response Topic | ✅ Yes | Per-message | `msg.responseTopic = "response/fromE3"` — only for request/reply |
| Correlation Data | ✅ Yes | Per-message | `msg.correlationData = msgId` — **required by E3** |
| Content Type | ✅ Yes | Per-message | `msg.contentType = "application/json"` — **required by E3** |
| User Property | ✅ Yes | Per-message | `msg.userProperties = {...}` — see section 4, this is your custom key/value slot |
| Subscription Identifier | ❌ No, broker/subscriber sets | Set by broker on delivery to a subscriber | Not something you set when publishing |

**Note:** unlike AMQP, MQTT v5 has no durable/priority equivalent per message — durability comes from **QoS** (set on the MQTT Out node config), and there's no message priority concept at all.

---

## 2. Message Annotations

Broker/infrastructure metadata (e.g. scheduled delivery hints). **You don't set these from NodeRed**, on either path. Skip this section for normal MES publishing — it's not a Function-node concern.

---

## 3. Properties (standard AMQP fields)

| AMQP Field | Customizable? | MQTT Out node | amqp-send node |
|---|---|---|---|
| `message-id` | ✅ Yes | No predefined MQTT field — put it in `msg.userProperties` instead | `msg.payload.message_id = myId` |
| `to` | N/A | `msg.topic = "fromAppToE3"` — this **is** your routing address | Set on the amqp-send node's **address/link** config, not per-message |
| `subject` | ✅ Yes | No predefined MQTT field — put it in `msg.userProperties` | `msg.payload.subject = "TrackIn Event"` |
| `reply-to` | ✅ Yes | `msg.responseTopic = "response/fromE3"` | `msg.payload.reply_to = "response-address"` |
| `correlation-id` | ✅ Yes | `msg.correlationData = msgId` — **required by E3** | `msg.payload.correlation_id = msgId` — **required by E3** |
| `content-type` | ✅ Yes | `msg.contentType = "application/json"` — **required by E3** | `msg.payload.content_type = "application/json"` — **required by E3** |
| `content-encoding` | ⚠️ Rarely needed | No dedicated field — skip unless E3 asks for it | `msg.payload.content_encoding = "utf-8"` |
| `absolute-expiry-time` / `creation-time` | ⚠️ Not directly | Use `msg.messageExpiryInterval` instead | Usually left to the broker; avoid setting manually |
| `group-id` | ✅ Yes (AMQP only) | ❌ Not exposed by MQTT Out | `msg.payload.group_id = "lot-12345"` — Artemis groups same-key messages to one consumer, preserving order |

**Note:** every field here is a direct key on `msg.payload` (not on `msg` itself, and not further nested under a `header`/`properties` sub-object) — confirmed against Artemis's own Properties view, which showed `properties.correlationId` and `properties.contentType` populated from exactly this shape.

---

## 4. Application Properties / User Properties (your main tool — this is what E3 reads)

| Protocol | Section name | Customizable? | `msg` field |
|---|---|---|---|
| AMQP 1.0 | Application Properties | ✅ Yes — free-form key/value map | `msg.payload.application_properties = {...}` (amqp-send node) |
| MQTT v5 | User Properties | ✅ Yes — free-form key/value map | `msg.userProperties = {...}` (MQTT Out node) |

These are **the same concept** in both protocols. This is where all custom business/routing data goes — E3, and any AMQP selector filter, reads from here. (Note: Artemis does **not** automatically translate AMQP Application Properties into MQTT User Properties when bridging between protocols at the broker level — that translation only happens if a NodeRed flow explicitly reads one and sets the other, as our MES flow does.)

**MQTT Out node:**
```javascript
msg.userProperties = {
  "action-name": "TRACKIN",
  "application-name": "E3_MES_Integration",   // underscores, not spaces!
  "source": "MES",
  "status": "200"
};
```

**amqp-send node:**
```javascript
msg.payload.application_properties = {
  "action-name": "TRACKIN",
  "application-name": "E3_MES_Integration",
  "source": "MES",
  "status": "200"
};
```
*(Confirmed in the Artemis console as `applicationProperties.*` entries under the message's Properties view.)*

**Rules of thumb:**
- Keys and values should be simple strings — avoid nested objects/arrays (keeps it interoperable and filterable).
- Anything E3 needs to filter or route on belongs here, not in the payload body.
- This is also what AMQP consumer **selectors** filter on (e.g. `action-name = 'TRACKIN'`) — same key/values either way.

---

## 5. Body

| | MQTT Out node | amqp-send node |
|---|---|---|
| Field | `msg.payload` **is** the body | `msg.payload.body` — one key among siblings |

```javascript
// MQTT Out
msg.payload = mesPayload;

// amqp-send
msg.payload = {
  body: mesPayload,
  content_type: "application/json",
  // ...other fields from sections 1/3/4 as siblings of "body"
};
```

Set the content-type field (section 3) so the receiver knows how to parse it.

---

## Quick Reference

### MQTT Out node (current E3 flow)
```javascript
msg.topic = "fromAppToE3";
msg.contentType = "application/json";
msg.correlationData = msgId;
msg.messageExpiryInterval = 3600;
msg.userProperties = {
  "action-name": "TRACKIN",
  "application-name": "E3_MES_Integration",
  "source": "MES",
  "status": "200"
};
msg.payload = mesPayload;
```

### amqp-send node (node-red-contrib-rhea)
```javascript
// Everything - header/properties fields, application_properties, and body -
// nests inside msg.payload as sibling keys.
msg.payload = {
  durable: true,
  ttl: 300000,
  correlation_id: msgId,
  content_type: "application/json",

  application_properties: {
    "action-name": "TRACKIN",
    "application-name": "E3_MES_Integration",
    "source": "MES",
    "status": "200"
  },

  body: mesPayload
};
```

Everything else in the AMQP spec (delivery-count, message annotations) is broker-managed — nothing to set on either path.

---

## A Note on Library Conventions vs. the Protocol Itself

Everything above describes how **this specific NodeRed setup** (`node-red-contrib-rhea` + `MQTT Out`) happens to expose AMQP fields — it is not a description of AMQP the protocol.

**AMQP 1.0 itself is never "flat."** The wire format genuinely groups fields into distinct sections (Header, Properties, Application Properties, Body). Whether a given client library or NodeRed wrapper represents that in code as flat attributes or as nested objects is purely **that library's own design choice**, and it varies:

- `python-qpid-proton` (used in `scripts/*.py`) — flattens Header/Properties fields directly onto its `Message` object (`msg.priority`, `msg.correlation_id`, `msg.subject`), keeping only application properties as a nested dict.
- `node-red-contrib-rhea`'s `amqp-send`/`amqp-recv` nodes — nests **everything**, body included, inside `msg.payload` as sibling keys.

Same protocol, same broker, two different representations. **Never assume a message shape "because it's AMQP" — check the specific library/node in use.** The Artemis-console round-trip (publish → browse the queue → inspect Headers/Properties) is the fastest way to confirm a given node's actual contract before building more flow logic on top of an assumption.

**Artemis does not auto-translate properties across protocols.** Publishing via AMQP with `application_properties` set does **not** automatically make those appear as MQTT v5 User Properties on a bridged MQTT subscriber, and the reverse is also true — Artemis's built-in AMQP↔MQTT bridging only reliably carries the message **body** across protocols. Getting `application_properties` ↔ `userProperties` translated requires an explicit NodeRed step that reads one and sets the other (exactly what `mesAmqpToMqttPublisher.js` does for the E3 flow) — there's no broker-level setting that does this automatically.

---

## Related Files

- Function node source (production, real AMQP data): `NodeRedScripts/mesAmqpToMqttPublisher.js`
- Function node source (superseded demo, hardcoded data): `NodeRedScripts/mesMQTTPublisher.js`
- AMQP-only republish flow: `NodeRedScripts/setupAmqpProperties.js`, `NodeRedScripts/copyPropertiesToHeader.js`
- Setup guide: `guides/nodered-mes-mqtt-publisher.md`
- Full input/output contracts for every node: `DataContracts.md`
- Example payload: `ExampleMessages/DestinationMessages/MES_TrackIn_v1.json`
