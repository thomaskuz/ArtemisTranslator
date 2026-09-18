/**
 * Setup AMQP Application Properties (NodeRed)
 *
 * Deviation of setupCloudEvent.js for a pure AMQP -> AMQP republish flow.
 * No CloudEvent envelope, no MQTT - the incoming "header" object is promoted
 * to real AMQP application properties, and the message is republished as-is
 * via the amqp-send node (node-red-contrib-rhea).
 *
 * IMPORTANT (node-red-contrib-rhea specific): amqp-send reads everything from
 * msg.payload as one object - body, application_properties, correlation_id,
 * content_type, etc. all live as sibling keys on msg.payload, NOT flat on msg
 * itself. See guides/amqp-message-fields-nodered.md for background.
 *
 * Expects: msg.parsedBody to be set (from prepareBody.js, unchanged - reuse it)
 *
 * Input:  msg.parsedBody.header       (any shape, field-agnostic)
 * Output: msg.payload.application_properties (flat key/value)
 *         msg.payload.correlation_id  (only if a correlation-id-like field is found)
 *         msg.payload.content_type    ("application/json")
 *         msg.payload.body            (the full message body, header included)
 *
 * Also clears msg.rawBody / msg.parsedBody / msg.bodyParsed - those were only
 * needed as intermediate state for prepareBody.js and would otherwise sit
 * around duplicating the same data as msg.payload for the rest of the flow.
 *
 * Copy this entire code into a NodeRed Function node, placed after prepareBody.
 */

if (!msg.parsedBody) {
  msg.error = 'parsedBody not set. Run prepareBody first.';
  node.status({ fill: 'red', shape: 'dot', text: 'Missing parsedBody' });
  return msg;
}

// Set to false to strip "header" out of the body once its fields are promoted
// to application_properties. On by default - header staying in both places is
// fine (nothing else in the body is duplicated), and keeps payload complete/unmodified.
const KEEP_HEADER_IN_BODY = true;

try {
  const header = msg.parsedBody.header || {};

  // Promote every header field to an AMQP application property.
  // Field-agnostic - no hardcoded key names, works with whatever "header" contains.
  const applicationProperties = {};
  for (const key in header) {
    if (header.hasOwnProperty(key)) {
      const value = header[key];
      // AMQP application properties must be simple scalars - stringify anything else
      applicationProperties[key] = (typeof value === 'object' && value !== null)
        ? JSON.stringify(value)
        : value;
    }
  }

  // Bonus: also set the real AMQP correlation-id property (not just an
  // application property) - usable for AMQP request/reply and standard
  // correlation, not only broker-side filtering.
  //
  // Field name is matched generically (case/separator-insensitive: matches
  // correlationId, correlationID, CorrelationId, correlation_id, Correlation-Id,
  // ...) since the exact key can differ between message types/versions.
  // It stays in application_properties too via the loop above - nothing removed.
  const correlationKey = Object.keys(header).find(
    (key) => /^correlation[-_]?id$/i.test(key)
  );

  const body = KEEP_HEADER_IN_BODY
    ? msg.parsedBody
    : Object.fromEntries(Object.entries(msg.parsedBody).filter(([k]) => k !== 'header'));

  // amqp-send (node-red-contrib-rhea) expects the full AMQP message as ONE
  // object on msg.payload - body and metadata as sibling keys.
  msg.payload = {
    body,
    application_properties: applicationProperties,
    content_type: 'application/json',
    ...(correlationKey !== undefined && { correlation_id: String(header[correlationKey]) })
  };

  // Drop intermediate fields from prepareBody.js - their data now lives in
  // msg.payload, keeping them around is pure duplication.
  delete msg.rawBody;
  delete msg.parsedBody;
  delete msg.bodyParsed;

  node.status({
    fill: 'green',
    shape: 'dot',
    text: `AMQP properties set (${Object.keys(applicationProperties).length})`
  });
  return msg;
} catch (error) {
  node.status({ fill: 'red', shape: 'dot', text: 'Error' });
  msg.error = `Failed to set AMQP properties: ${error.message}`;
  return msg;
}
