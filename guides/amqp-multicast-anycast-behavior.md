# AMQP Multicast and Anycast Behavior in Artemis

Comprehensive guide to understanding how Artemis routes messages differently based on address routing type, and how this affects message delivery to AMQP consumers.

## Quick Summary

| Aspect | Multicast | Anycast |
|--------|-----------|---------|
| **Message Routing** | One message → ALL queues | One message → ONE queue |
| **Use Case** | Broadcast/fan-out | Load balancing |
| **Queues Needed** | Multiple queues on same address | One queue per address |
| **Message Duplication** | Yes (stored in each queue) | No (goes to one queue) |
| **Late Subscribers** | See messages if queue has them | Load-balanced distribution |

---

## Part 1: Multicast Addresses

### What is Multicast?

A **multicast address** delivers a SINGLE incoming message to ALL bound queues on that address.

```
Publisher → Address "events" (Multicast)
                     ├─ Queue A ← receives copy
                     ├─ Queue B ← receives copy
                     └─ Queue C ← receives copy
```

### Use Cases for Multicast

1. **Fan-out / Broadcast** — One message needs to reach multiple consumers
2. **Multiple subscribers** — Different departments need the same event
3. **Message duplication** — Intentional replication for resilience
4. **Protocol bridging** — Same message for AMQP and MQTT consumers

### Multicast Example: Event Broadcasting

```
FileManager Status Event
    ↓
Address: "status-events" (Multicast)
    ├─ Queue: "audit-log" → Event persisted for compliance
    ├─ Queue: "realtime-monitoring" → Event for live dashboard
    ├─ Queue: "backup-archive" → Event for long-term storage
    └─ MQTT Topic → Event for external subscribers
```

Each subscriber sees the complete event.

---

## Part 2: Anycast Addresses

### What is Anycast?

An **anycast address** delivers an incoming message to ONE bound queue (load balancing).

```
Publisher → Address "tasks" (Anycast)
                ↓
            Picks ONE queue
                ├─ Queue A ← receives message
                ├─ Queue B (skipped)
                └─ Queue C (skipped)

Next message:
                ├─ Queue A (skipped)
                ├─ Queue B ← receives message
                └─ Queue C (skipped)
```

### Load Balancing Algorithm

Artemis distributes messages round-robin:
- Message 1 → Queue A
- Message 2 → Queue B
- Message 3 → Queue C
- Message 4 → Queue A
- (repeat...)

### Use Cases for Anycast

1. **Load balancing** — Distribute work across multiple workers
2. **Single destination** — One logical queue, multiple instances
3. **Work queues** — Task processing with multiple consumers
4. **Resource efficiency** — Avoid message duplication

### Anycast Example: Job Processing

```
Job Queue System
    ↓
Address: "jobs" (Anycast)
    ├─ Queue: "worker-1" ← Job A
    ├─ Queue: "worker-2" ← Job B
    └─ Queue: "worker-3" ← Job C
```

Each job goes to ONE worker (no duplication).

---

## Part 3: Address vs Queue for AMQP Consumers

### Critical Distinction: Consuming from Address vs Queue

When you create an AMQP consumer, you can connect to either an **address** or a **queue**. This choice dramatically affects what messages you receive.

### Consumer Type 1: Address Consumer (Real-Time Only)

```python
# Connect to ADDRESS (not a specific queue)
consumer = event.container.create_receiver(event.connection, "amqp-mqtt-bridge")
```

**Behavior:**
- Creates a temporary, anonymous queue for this session
- Only receives messages arriving AFTER subscription
- Does NOT see historical/stored messages
- Temporary queue is deleted when consumer disconnects

**Message Flow:**
```
Publisher sends → Address
                     ├─ bridge-queue (persisted) ← stores message
                     └─ consumer's temp queue ← receives message (if connected)

If consumer connects AFTER:
  └─ consumer's temp queue ← receives ONLY NEW messages (not the stored one)
```

**Characteristics:**
- ✅ Real-time delivery
- ✅ No message acknowledgment required
- ❌ No message persistence
- ❌ No catch-up for late subscribers
- ❌ Messages lost if subscriber disconnects

**Use Case:** Live event monitoring, streaming data, MQTT-like behavior

**Example:**
```
T=0s  Message #1 published
T=1s  Message #2 published
T=2s  CONSUMER A connects to ADDRESS
        Receives: [Message #3, #4, #5, ...]
        Misses: Message #1, #2 (arrived before connection)
```

### Consumer Type 2: Queue Consumer (Real-Time + Historical)

```python
# Connect to QUEUE (specific queue on address)
consumer = event.container.create_receiver(event.connection, "bridge-queue")
```

**Behavior:**
- Connects directly to a durable queue
- Receives ALL messages in the queue (historical + new)
- Messages persist until acknowledged
- Can catch up on missed messages

**Message Flow:**
```
Publisher sends → Address
                     └─ bridge-queue (persisted) ← stores message

CONSUMER B connects to QUEUE:
  ├─ Receives message #1 (stored)
  ├─ Receives message #2 (stored)
  ├─ Receives message #3 (new)
  └─ Receives message #4 (new)
```

**Characteristics:**
- ✅ Real-time AND historical delivery
- ✅ Message persistence (durable queues)
- ✅ Message acknowledgment
- ✅ Catch-up for late subscribers
- ✅ Reliable message delivery
- ❌ Requires message acknowledgment
- ❌ Storage overhead

**Use Case:** Reliable message processing, store-and-forward, order processing

**Example:**
```
T=0s  Message #1 published → stored in bridge-queue
T=1s  Message #2 published → stored in bridge-queue
T=2s  CONSUMER B connects to QUEUE
        Receives: [Message #1, #2, #3, #4, ...] (all messages)
        Catches up: Message #1, #2 (from storage)
```

---

## Part 4: Multicast with Address vs Queue Consumers

### The Complete Picture

When you have a **multicast address** with multiple queues, the routing works like this:

```
Publisher → Multicast Address "events"
                  ├─ Queue A (durable)
                  ├─ Queue B (durable)
                  └─ Temporary Address Consumer Queue (ephemeral)
```

**Incoming message:**
1. Published to address "events"
2. Address type is MULTICAST
3. Message stored in Queue A
4. Message stored in Queue B
5. Message sent to address consumer's temp queue (if connected)

### Scenario: Three Different Consumers

```
Multicast Address: "events"
├─ Queue: "archive-queue" (durable, for long-term storage)
├─ Queue: "analytics-queue" (durable, for analysis)
└─ No explicit persistent queue for real-time monitoring
```

**Timeline:**
```
T=0s   Event #1 published
       → stored in archive-queue
       → stored in analytics-queue
       → no real-time consumer, so no temp queue

T=1s   Real-time Monitor connects to ADDRESS "events"
       → Creates temp queue for this session
       → Receives: [Event #2, #3, #4, ...]
       → Misses: Event #1 (missed before connection)

T=2s   Archive Consumer connects to QUEUE "archive-queue"
       → Receives: [Event #1, #2, #3, #4, ...]
       → Catches up: Event #1 (stored in queue)

T=3s   Analytics Consumer connects to QUEUE "analytics-queue"
       → Receives: [Event #1, #2, #3, #4, ...]
       → Catches up: Event #1 (stored in queue)
```

**Results:**
- Real-time Monitor: sees Event #2+ (live only)
- Archive Consumer: sees Event #1+ (all messages)
- Analytics Consumer: sees Event #1+ (all messages)

---

## Part 5: Practical Implications for AMQP-MQTT Bridging

### AMQP-MQTT Bridge Setup

```
Multicast Address: "amqp-mqtt-bridge"
├─ Queue: "bridge-queue" (durable AMQP queue)
└─ MQTT Subscribers (create temp queues per session)
```

### Message Delivery Behavior

| Consumer Type | Receives Real-Time | Receives Historical | Delivery Guarantee |
|---------------|------------------|---------------------|-------------------|
| **MQTT Subscriber** | ✅ Yes (address) | ❌ No | Best-effort (QoS 1) |
| **AMQP Consumer on bridge-queue** | ✅ Yes | ✅ Yes | Reliable |

### Timeline Example

```
Publisher sends Message #1 → amqp-mqtt-bridge
  ├─ Stored in bridge-queue (persistent)
  ├─ Sent to MQTT subscribers (if connected)

MQTT Subscriber A connects
  Receives: [Message #2, #3, #4, ...] (only new)

AMQP Consumer connects to bridge-queue
  Receives: [Message #1, #2, #3, #4, ...] (all messages)
```

---

## Part 6: Queues and Message Storage

### Queue Persistence

**Durable Queue:**
```
bridge-queue (durable=true)
├─ Message persists to disk
├─ Survives broker restart
├─ Consumer receives on connect
```

**Non-Durable Queue:**
```
temp-queue (durable=false)
├─ Message kept in memory
├─ Lost on broker restart
├─ Created/destroyed per session
```

### Creating Queues for Multicast

**For AMQP consumers** (want history):
```
Name: bridge-queue
Address: amqp-mqtt-bridge (Multicast)
Durable: true  ← Important for persistence
```

**For multiple consumers**:
```
Multicast Address: "amqp-mqtt-bridge"
├─ Queue: "archive-queue" (durable=true)
├─ Queue: "monitoring-queue" (durable=true)
└─ Queue: "backup-queue" (durable=true)
```

Each queue independently stores all messages.

---

## Part 7: Design Decisions

### When to Use Multicast?

**Choose Multicast when:**
- ✅ Multiple subscribers need the same message
- ✅ You want protocol bridging (AMQP + MQTT)
- ✅ You need fan-out/broadcast behavior
- ✅ Duplicate storage is acceptable
- ✅ Multiple independent systems consume the same event

**Example:** FileManager publishes status → both monitoring system AND archival system need it

### When to Use Anycast?

**Choose Anycast when:**
- ✅ Only one queue needs the message
- ✅ You want load balancing across workers
- ✅ You want to avoid storage duplication
- ✅ Messages are for specific tasks/jobs
- ✅ You want efficient resource usage

**Example:** Job queue with 3 workers (distribute load)

### Hybrid Approach

Use BOTH in the same system:

```
Events System
├─ Address: "commands" (Anycast) → Load balance to worker pool
├─ Address: "status-events" (Multicast)
│   ├─ Queue: "monitoring"
│   ├─ Queue: "archival"
│   └─ MQTT subscribers
└─ Address: "alerts" (Multicast)
    ├─ Queue: "sms-queue"
    ├─ Queue: "email-queue"
    └─ Queue: "slack-queue"
```

---

## Part 8: Message Flow Diagrams

### Multicast Flow

```
┌─────────────┐
│  Publisher  │
└──────┬──────┘
       │ Send to "events"
       ▼
┌─────────────────────────────────┐
│ Multicast Address: "events"     │
└─────────────────────────────────┘
       │
       ├─────────────────┬──────────────┬──────────────┐
       ▼                 ▼              ▼              ▼
   ┌────────┐        ┌────────┐   ┌────────┐   ┌──────────┐
   │ Queue A│        │ Queue B│   │ Queue C│   │Temp Queue│
   │(persist)       │(persist)   │(persist)   │(session) │
   └────────┘        └────────┘   └────────┘   └──────────┘
       │                 │              │          │
       ▼                 ▼              ▼          ▼
  Consumer A        Consumer B    Consumer C   Real-time
  (all msgs)        (all msgs)    (all msgs)   Monitor
                                              (new only)
```

### Anycast Flow

```
┌─────────────┐
│  Publisher  │
└──────┬──────┘
       │ Send to "tasks"
       ▼
┌─────────────────────────────────┐
│ Anycast Address: "tasks"        │
│ (round-robin to one queue)      │
└─────────────────────────────────┘
       │
       ├──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
   ┌────────┐    ┌────────┐    ┌────────┐
   │ Queue A│ or │ Queue B│ or│ Queue C│
   │(only 1)    │(only 1)    │(only 1)
   └────────┘    └────────┘    └────────┘
       │              │              │
       ▼              ▼              ▼
   Worker A      Worker B      Worker C
   (load bal.)   (load bal.)   (load bal.)
```

---

## Part 9: Common Mistakes

### Mistake 1: Expecting Address Consumer to Get History

**❌ Wrong:**
```python
# Connect to ADDRESS, expect all messages
consumer = event.container.create_receiver(event.connection, "events")
# Only gets messages after this line executes!
```

**✅ Correct:**
```python
# Connect to QUEUE to get all messages
consumer = event.container.create_receiver(event.connection, "archive-queue")
# Gets all messages in queue (including stored ones)
```

### Mistake 2: Using Multicast for Single Recipient

**❌ Wrong:** (wastes storage)
```
Multicast Address with 1 queue
└─ Queue: "single-queue" ← Only one consumer
```

**✅ Correct:**
```
Anycast Address with 1 queue
└─ Queue: "single-queue" ← Same routing, less overhead
```

### Mistake 3: Forgetting Queue Durability

**❌ Wrong:** (loses messages on restart)
```
Queue: "events"
Durable: false
├─ Messages lost on broker restart
└─ Historical data gone
```

**✅ Correct:**
```
Queue: "events"
Durable: true
├─ Messages persist to disk
└─ Survives restarts
```

### Mistake 4: Not Creating Explicit Queues

**❌ Wrong:** (MQTT only, no AMQP history)
```
Multicast Address: "events"
├─ No explicit queues (only MQTT temp queues)
├─ MQTT: sees real-time only
└─ No storage for AMQP consumers
```

**✅ Correct:**
```
Multicast Address: "events"
├─ Queue: "bridge-queue" (durable)
├─ MQTT: sees real-time
└─ AMQP consumers: can read history
```

---

## Part 10: Testing and Verification

### Test 1: Verify Multicast Routing

**Setup:**
```
Multicast Address: "test-multicast"
├─ Queue A
├─ Queue B
└─ Queue C
```

**Test:**
1. Send 1 message to address
2. Check Artemis Console → Queues
3. Expected: All 3 queues show 1 message

**Result:**
```
Queue A: 1 message ✅
Queue B: 1 message ✅
Queue C: 1 message ✅
```

### Test 2: Verify Anycast Load Balancing

**Setup:**
```
Anycast Address: "test-anycast"
├─ Queue A
├─ Queue B
└─ Queue C
```

**Test:**
1. Send 3 messages to address
2. Check Artemis Console → Queues
3. Expected: Messages distributed round-robin

**Result:**
```
Queue A: 1 message ✅
Queue B: 1 message ✅
Queue C: 1 message ✅
```

### Test 3: Address vs Queue Consumer

**Setup:**
```
Multicast Address: "test-address"
├─ Queue: "persistent-queue"
```

**Test:**
1. Publish message #1
2. Create address consumer
3. Publish message #2
4. Create queue consumer

**Address Consumer receives:**
```
[Message #2, Message #3, ...] (only new)
```

**Queue Consumer receives:**
```
[Message #1, Message #2, Message #3, ...] (all)
```

---

## Summary Table: Quick Reference

| Scenario | Routing | Consumer Type | Receives |
|----------|---------|---------------|----------|
| Fan-out to multiple teams | Multicast | Queue | All messages |
| Live real-time events | Multicast | Address | New only |
| Load balance work | Anycast | Queue | Next message |
| AMQP-MQTT bridge | Multicast | Queue (AMQP) + Address (MQTT) | All (AMQP) + New (MQTT) |
| Archive all events | Multicast | Queue (durable) | All (persisted) |

---

## Next Steps

1. ✅ Decide: Multicast or Anycast for your use case?
2. ✅ Create appropriate queues
3. ✅ Choose consumer type: Address (real-time) or Queue (reliable)
4. ✅ Set durability based on your persistence needs
5. ✅ Test with multiple consumers
6. ✅ Verify message distribution in Artemis Console
7. ✅ Monitor queue depths for bottlenecks

---

## Related Guides

- [AMQP to MQTT Bridging](amqp-mqtt-bridging.md) — Practical example using multicast
- [Multiple Message Filtering](multiple-message-filtering.md) — Multicast with filter routing
- [Message Transformation & Filtering](nodered-message-transformation-filtering.md) — Real-world multicast scenario
