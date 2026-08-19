/**
 * Prepare Body Function (NodeRed)
 *
 * Extracts and parses the body from incoming AMQP message
 * Handles both string and object formats
 *
 * Input: msg with payload.body (string or object)
 * Output: msg with msg.parsedBody (object) and msg.rawBody (original)
 *
 * Copy this entire code into a NodeRed Function node
 */

// Extract body from incoming message
const body = msg.payload.body || msg.payload;

// Store raw body for reference
msg.rawBody = body;

// Recursively parse JSON strings within objects
function deepParseJSON(obj) {
  if (typeof obj === 'string') {
    try {
      // Try to parse the string as JSON
      return deepParseJSON(JSON.parse(obj));
    } catch (e) {
      // Not JSON, return as-is
      return obj;
    }
  } else if (typeof obj === 'object' && obj !== null) {
    // Recursively parse all properties
    const parsed = Array.isArray(obj) ? [] : {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        parsed[key] = deepParseJSON(obj[key]);
      }
    }
    return parsed;
  }
  // Return primitives as-is
  return obj;
}

// Parse body based on type
try {
  if (typeof body === 'string') {
    // Parse string to JSON, then recursively parse nested strings
    const parsed = JSON.parse(body);
    msg.parsedBody = deepParseJSON(parsed);
  } else if (typeof body === 'object') {
    // If already object, recursively parse nested strings
    msg.parsedBody = deepParseJSON(body);
  } else {
    // Fallback: wrap in object
    msg.parsedBody = { data: body };
  }

  // Also update msg.payload.body with parsed content so it flows through the pipeline
  if (msg.payload && typeof msg.payload === 'object') {
    msg.payload.body = msg.parsedBody;
  } else {
    msg.payload = msg.parsedBody;
  }

  msg.bodyParsed = true;
  node.status({ fill: 'green', shape: 'dot', text: 'Body parsed successfully' });
} catch (error) {
  msg.bodyParsed = false;
  msg.error = `Failed to parse body: ${error.message}`;
  node.status({ fill: 'red', shape: 'dot', text: 'Parse error' });
}

return msg;
