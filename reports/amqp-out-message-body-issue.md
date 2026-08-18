# AMQP Out Message Body Issue - Resolved

## Problem
The `@meowwolf/node-red-contrib-amqp` AMQP Out node was not sending message bodies to Artemis. Messages arrived in the queue but with empty bodies.

## What Wasn't Working
```javascript
// ❌ FAILED - Body arrived as None
msg.payload = "Test message";
```

Even though messages were successfully received in Artemis, the consumer showed `Body: None`.

## Root Cause
The AMQP Out node expects messages in a **specific wrapped format** that matches the structure produced by the AMQP In node. When we just set `msg.payload` to a string, the node didn't recognize it as a valid message body.

## Solution
Wrap the message in the format that AMQP In/Out nodes expect:

```javascript
// ✅ WORKS - Body now arrives with content
msg.payload = {
    body: JSON.stringify({
        commander: "Thomas",
        message_number: 1,
        timestamp: new Date().toISOString()
    })
};
```

## Key Learnings
1. **AMQP In/Out nodes speak the same language** — Use the wrapped format for both
2. **Message structure matters** — The node checks for specific properties, not just `msg.payload`
3. **Test with consumers** — Use Python consumer to verify what's actually being sent
4. **Debug the full message** — Set Debug nodes to "Complete msg object" to see structure

## How to Apply
When using NodeRed AMQP In/Out nodes:
- Always wrap messages: `msg.payload = { body: "...", applicationProperties: {...} }`
- Match the format from AMQP In debug output
- Test with consumers to verify actual content
