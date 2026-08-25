# AMQP to MQTT Bridging on Artemis

Complete guide for bridging AMQP and MQTT protocols on the same Artemis broker, allowing messages published via AMQP to be consumed via MQTT and vice versa.

## Key Concept: Multicast Address Required

**Important:** AMQP and MQTT use different protocol semantics and do NOT automatically share the same queues in Artemis. To bridge them, you **must use a multicast address**.

- **Anycast Address** → Messages go to ONE queue (no protocol sharing)
- **Multicast Address** → Messages go to ALL queues on that address (AMQP + MQTT share messages)

## Architecture

```
AMQP Publisher                MQTT Subscriber
    ↓                              ↑
    └──→ amqp-mqtt-bridge ←────┘
         (Multicast Address)
         └─ bridge-queue (AMQP consumer)
         └─ MQTT session queue (MQTT consumer)
```

## Prerequisites

- ✅ Artemis running on port 5672 (AMQP) and 1883 (MQTT)
- ✅ Python 3 with `python-qpid-proton` and `paho-mqtt` installed
- ✅ Artemis configured with MQTT protocol enabled (default in latest versions)

## Step 1: Configure Artemis for MQTT

### Verify MQTT is Enabled

1. SSH into Artemis container or check broker config at `/var/lib/artemis-instance/etc/broker.xml`
2. Look for MQTT acceptor:
   ```xml
   <acceptor name="mqtt">tcp://0.0.0.0:1883?...protocols=MQTT;...</acceptor>
   ```
3. Ensure port 1883 is exposed in docker-compose.yml:
   ```yaml
   ports:
     - "1883:1883"  # MQTT protocol
   ```

## Step 2: Create Multicast Address & Queue

### In Artemis Admin Console (http://localhost:8161)

**Create the Address:**
1. Click **Addresses** tab
2. Click **Create Address**
3. Fill in:
   - **Name**: `amqp-mqtt-bridge`
   - **Routing type**: `Multicast` ← **CRITICAL!**
4. Click **Create**

**Create the Queue:**
1. Click **Queues** tab
2. Click **Create Queue**
3. Fill in:
   - **Name**: `bridge-queue`
   - **Address**: `amqp-mqtt-bridge`
   - **Durable**: ✅ `true`
4. Click **Create**

### Why Multicast?

When you publish an AMQP message to `amqp-mqtt-bridge`, Artemis will:
1. Deliver to `bridge-queue` (AMQP consumer)
2. Deliver to all MQTT subscriber session queues (MQTT consumers)
3. Both protocol consumers see the SAME message

Without multicast, AMQP and MQTT maintain separate queue spaces.

## Step 3: Update Python Scripts

### AMQP Publisher

All AMQP publisher scripts should send to address `amqp-mqtt-bridge`:

```python
def main():
    broker = "amqp://admin:admin@localhost:5672"
    address = "amqp-mqtt-bridge"  # Send to multicast address
    
    handler = Publisher(broker, address, message_template)
    # ... rest of setup
```

**Note on Terminology:**
- In code, we call it `address` (not `queue`)
- The AMQP publisher sends to an **address**
- The address routes to all bound queues (AMQP + MQTT)

Available publisher scripts:
- `simple_publisher_amqp.py` — Simple messages
- `publisher_with_headers_amqp.py` — Messages with AMQP headers
- `publisher_with_headers_extended_amqp.py` — All metadata types

### MQTT Subscriber

Subscribe to the same address/topic:

```python
def main():
    broker = "localhost"
    port = 1883
    topic = "amqp-mqtt-bridge"  # Subscribe to same address
    
    subscriber = MQTTSubscriber(broker, port, topic)
    subscriber.start()
```

**MQTT Authentication:**
- Username: `admin`
- Password: `admin`
- (These match Artemis admin credentials)

## Step 4: Run the Test

### Terminal 1: Start MQTT Subscriber

```bash
python mqtt_subscriber.py
```

Expected output:
```
[...] Starting MQTT Subscriber
[...] Will subscribe to: amqp-mqtt-bridge
[...] This tests AMQP → MQTT bridging in Artemis

[...] Connecting to Artemis MQTT at localhost:1883...
[✓] Connected to Artemis MQTT (localhost:1883)
[!] Subscribed to topic: amqp-mqtt-bridge
[!] Waiting for messages (Ctrl+C to stop)
```

### Terminal 2: Start AMQP Publisher

```bash
python simple_publisher_amqp.py
```

Expected output:
```
[...] Starting simple publisher (sending to amqp-mqtt-bridge)...

[✓] Connected to Artemis
[✓] Sender ready for address: amqp-mqtt-bridge
[!] Sending messages every 5 seconds (Ctrl+C to stop)

[✓] Sent message #1
    Body: {"color": "Red", "message_number": 1}
```

### Terminal 1: MQTT Subscriber Receives Messages

```
======================================================================
[✓] Message #1 received on MQTT
======================================================================
Topic: amqp-mqtt-bridge
QoS: 1

Payload (JSON):
{
  "color": "Red",
  "message_number": 1
}

======================================================================
```

## What's Happening Behind the Scenes

1. **AMQP Publisher sends** → `{"color": "Red", "message_number": 1}`
2. **Artemis receives** on address `amqp-mqtt-bridge`
3. **Artemis routes to**:
   - `bridge-queue` (AMQP side)
   - MQTT session queues (MQTT side)
4. **MQTT Subscriber receives** the same message

## Verifying in Artemis Console

Go to **http://localhost:8161**:

1. **Queues** tab:
   - `bridge-queue` → Shows count of messages (AMQP side)
   - `artemis-mqtt-subscriber.amqp-mqtt-bridge` → Shows MQTT session messages

2. **Addresses** tab:
   - `amqp-mqtt-bridge` → Type: `Multicast`

3. Message details:
   - Click on a message to see full body and properties
   - Verify both AMQP and MQTT queues have the message

## Troubleshooting

### MQTT Connection Refused (error code 5)

**Problem:** Subscriber fails to connect to MQTT

**Solutions:**
1. ✅ Verify MQTT port 1883 is exposed in docker-compose.yml
2. ✅ Check Artemis container is healthy: `docker-compose ps`
3. ✅ Verify credentials: username `admin`, password `admin`
4. ✅ Check broker has MQTT acceptor enabled in broker.xml

### Messages Not Appearing in MQTT Subscriber

**Problem:** Publisher sends messages but subscriber doesn't receive them

**Solutions:**
1. ✅ Verify address is **Multicast**, not Anycast
2. ✅ Check subscriber is subscribing to `amqp-mqtt-bridge` (exact match)
3. ✅ Verify publisher is sending to `amqp-mqtt-bridge` (exact match)
4. ✅ Check message count in Artemis Console → Queues
5. ✅ Manually verify message in console by clicking on it

### Publisher Only Sends One Message

**Problem:** Publisher sends a message then stops

**Solution:**
- Verify timer is rescheduling itself in `on_timer_task()`:
  ```python
  def on_timer_task(self, event):
      if time.time() - self.last_send_time >= 5:
          self.send_message()
      event.container.schedule(1.0, self)  # ← Must reschedule!
  ```

## Understanding Address vs Queue

| Concept | AMQP Term | Meaning |
|---------|-----------|---------|
| **Address** | Target destination | Logical routing endpoint (e.g., "amqp-mqtt-bridge") |
| **Queue** | Persistent storage | Physical queue on an address (e.g., "bridge-queue") |
| **Multicast** | Routing behavior | One message → All queues on address |
| **Anycast** | Routing behavior | One message → One queue (load balancing) |

When AMQP publisher sends to `amqp-mqtt-bridge`, it's sending to an **address**. The multicast routing delivers that message to all queues bound to that address.

### Important: Address vs Queue for AMQP Consumers

When consuming messages with an AMQP consumer, the choice between **address** and **queue** determines what messages you receive:

#### Consuming from Address (Real-Time Only)

```python
# Consumer subscribes to ADDRESS
consumer = event.container.create_receiver(event.connection, "amqp-mqtt-bridge")
```

**Behavior:**
- ✅ Receives ONLY **real-time messages** (messages arriving AFTER subscription)
- ❌ Does NOT receive historical/stored messages
- ❌ No message persistence

**Use Case:** Live monitoring, real-time event processing (like MQTT subscribers)

#### Consuming from Queue (Real-Time + Historical)

```python
# Consumer subscribes to specific QUEUE on the address
consumer = event.container.create_receiver(event.connection, "bridge-queue")
```

**Behavior:**
- ✅ Receives BOTH real-time messages AND historical messages
- ✅ Messages are persisted in the queue (durable storage)
- ✅ Consumer can catch up on missed messages

**Use Case:** Reliable message processing, store-and-forward, message archiving

#### Comparison Table

| Aspect | Address Consumer | Queue Consumer |
|--------|------------------|-----------------|
| **Real-time messages** | ✅ Yes | ✅ Yes |
| **Historical messages** | ❌ No | ✅ Yes |
| **Persistence** | ❌ No | ✅ Yes (if durable) |
| **Message acknowledgment** | ❌ No | ✅ Yes |
| **Late subscribers** | Get only new msgs | Get all msgs (from start) |
| **Use case** | Live events | Reliable delivery |

#### Example Scenario

**Multicast Address:** `amqp-mqtt-bridge`  
**Queue on Address:** `bridge-queue` (durable)

**Timeline:**
```
T=0s   Message #1 published → stored in bridge-queue
T=2s   Message #2 published → stored in bridge-queue
T=5s   CONSUMER A subscribes to ADDRESS
         Receives: [Message #3, #4, #5, ...] (only new ones after T=5s)
         Misses: Message #1, #2 (already published before subscription)

T=5s   CONSUMER B subscribes to QUEUE
         Receives: [Message #1, #2, #3, #4, #5, ...] (all messages)
         Gets history: Message #1, #2 (already in queue)
```

**For the AMQP-MQTT Bridge Test:**
- **MQTT Subscribers** receive real-time messages (like address consumers)
- **AMQP Consumers** on `bridge-queue` receive all messages (like queue consumers)

## Complete Flow Example

### Scenario: Send 3 Messages

**Publisher script runs:**
```bash
python simple_publisher_amqp.py
```

**Message #1 at 0s:**
- Published via AMQP to address `amqp-mqtt-bridge`
- Delivered to `bridge-queue` (AMQP)
- Delivered to MQTT subscriber
- MQTT subscriber receives and displays

**Message #2 at 5s:**
- Same flow
- Subscriber displays in realtime

**Message #3 at 10s:**
- Same flow
- All 3 messages now in queues

### In Artemis Console:
- `bridge-queue`: 3 messages
- Multicast address distributes all 3 to MQTT
- MQTT subscriber has received 3

## Advanced: Bidirectional Bridging

For messages to flow BOTH ways (MQTT → AMQP and AMQP → MQTT):

1. ✅ Already configured with multicast address
2. Create an MQTT publisher (connect to port 1883)
3. Create an AMQP consumer on `amqp-mqtt-bridge`

Both will see the same messages automatically.

## Production Considerations

### Security
- ✅ Use strong credentials (not `admin:admin`)
- ✅ Configure Artemis security-settings for role-based access
- ✅ Use TLS/SSL for MQTT (port 8883 with certificates)

### Reliability
- ✅ Set queue durability to `true`
- ✅ Use QoS 1 or 2 for MQTT (at least once delivery)
- ✅ Configure message TTL based on your use case

### Performance
- ✅ Monitor queue sizes in Artemis Console
- ✅ Consider message batching for high throughput
- ✅ Adjust broker memory settings (-Xmx) if needed

## Testing Checklist

- ✅ Create multicast address `amqp-mqtt-bridge`
- ✅ Create queue `bridge-queue` on that address
- ✅ Verify MQTT port 1883 is exposed
- ✅ Start MQTT subscriber
- ✅ Start AMQP publisher
- ✅ See messages arrive in MQTT subscriber
- ✅ Verify counts in Artemis Console
- ✅ Check message details in console

## Key Learnings

1. **Multicast is essential** — Without it, AMQP and MQTT are isolated
2. **Terminology matters** — Publishers send to **addresses**, not queues
3. **Authentication required** — MQTT needs credentials (admin:admin)
4. **Port exposure critical** — Must expose 1883 in docker-compose
5. **Message delivery is automatic** — Multicast handles all routing
6. **Queue naming** — MQTT creates session queues automatically (prefixed with client ID)

## Next Steps

1. ✅ Test simple message flow (this guide)
2. ✅ Add message headers/metadata with `publisher_with_headers_amqp.py`
3. ✅ Set up multiple MQTT subscribers on same address
4. ✅ Create MQTT publisher and test bidirectional flow
5. ✅ Integrate with NodeRed for transformations
6. ✅ Set up persistent storage and recovery scenarios
