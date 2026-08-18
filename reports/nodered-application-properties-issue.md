# NodeRed Application Properties Issue - Resolved

## Problem
Application properties were not appearing in messages sent from NodeRed AMQP Out node to Artemis. The message body was transmitted correctly, but custom application properties (commander, message_number, etc.) were completely missing.

## What Wasn't Working

### Attempt 1: CamelCase Format
```javascript
msg.payload = {
    body: JSON.stringify({...}),
    applicationProperties: {  // ❌ camelCase
        commander: "Thomas",
        message_number: 1
    }
};
```

**Result:** Message body sent correctly, but NO application properties appeared in Artemis.

### Attempt 2: Top-Level Properties
```javascript
msg.payload = {
    body: JSON.stringify({...})
};

msg.properties = {  // ❌ top-level msg object
    commander: "Thomas"
};
```

**Result:** Messages stopped arriving entirely — broke the message format.

## Root Cause

The `@meowwolf/node-red-contrib-amqp` AMQP Out node expects messages in a **very specific wrapped format** that mirrors the AMQP In node's output structure:

- **AMQP In outputs:** `msg.payload.application_properties` (with underscore, lowercase)
- **AMQP Out expects:** `msg.payload.application_properties` (same format)

The node was strict about the field name and location — it had to be:
1. Nested inside `msg.payload` (not at top level)
2. Named `application_properties` (underscore, not camelCase)
3. Properly formatted as an object

## Solution

Use the exact format that AMQP In produces:

```javascript
// ✅ WORKS - Correct wrapped format
msg.payload = {
    body: JSON.stringify({
        original: incomingBody,
        transformation_status: "success",
        processed_at: new Date().toISOString()
    }),
    application_properties: {  // ✅ underscore, nested in payload
        commander: commander,
        message_number: messageNumber,
        transformed: true,
        source: "NodeRed-transformer"
    }
};

return msg;
```

**Result:** ✅ Both body AND application properties appear in Artemis

## Key Learnings

### 1. **AMQP In/Out Nodes Use Symmetric Format**
When debugging NodeRed AMQP issues:
- Use Debug node to see exactly how AMQP In structures messages
- Mirror that structure for AMQP Out
- Don't guess at field names or nesting

### 2. **Naming Matters**
- `application_properties` (underscore) ✅
- `applicationProperties` (camelCase) ❌
- This is how AMQP 1.0 spec structures them in AMQP protocol

### 3. **Message Structure is Strict**
The @meowwolf node validates message format:
- Top-level `msg.properties` breaks the message
- Only nested `msg.payload.application_properties` works
- Breaking the format = messages stop arriving

### 4. **Test with Consumers**
Always verify what's actually being sent:
```bash
python consumer_with_headers.py
```

Debug output in Artemis might be incomplete; Python consumers show full message structure.

## Transformation Flow (Now Working)

```
Input (test.queue)
    ↓ AMQP In
    ↓ [message with body]
    ↓ Function node
    ├─ Parse body JSON
    ├─ Extract commander
    ├─ Create transformed body
    └─ Set application_properties
    ↓ AMQP Out
    ↓ Output (transform.queue)
    ↓ [message with body + application_properties]
```

## What to Remember

When working with NodeRed AMQP nodes:
1. **Symmetric format:** AMQP In output = AMQP Out input structure
2. **Underscore notation:** `application_properties`, not `applicationProperties`
3. **Nested in payload:** `msg.payload.application_properties`, not `msg.properties`
4. **Validate with consumers:** Always check what's actually sent/received
5. **One step at a time:** Get body working first, then add properties
