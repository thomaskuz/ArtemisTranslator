/**
 * Copy Application Properties into Body Header (NodeRed)
 *
 * Reverse of setupAmqpProperties.js: takes an AMQP message straight from
 * amqp-recv (node-red-contrib-rhea), copies its application_properties into
 * a "header" object inside the body, and republishes via amqp-send.
 *
 * IMPORTANT (node-red-contrib-rhea specific): amqp-send requires the message
 * as ONE object on msg.payload, with body/application_properties/etc. as
 * sibling keys - see guides/amqp-message-fields-nodered.md. This output is
 * built to that exact contract (same shape setupAmqpProperties.js produces),
 * so it can be wired straight into amqp-send.
 *
 * Input:  msg.payload.application_properties (flat key/value, from amqp-recv)
 *         msg.payload.body                    (the message body - object or JSON string)
 *         msg.payload.correlation_id          (optional - added to header only if no
 *                                              application_properties field already
 *                                              looks like a correlation id)
 * Output: msg.payload.body.header             (application_properties fields, field-agnostic)
 *         msg.payload.application_properties  (carried over unchanged, for amqp-send)
 *         msg.payload.correlation_id          (carried over, if present)
 *         msg.payload.content_type            (carried over, if present)
 *
 * Copy this entire code into a NodeRed Function node, placed after amqp-recv
 * (and wired directly into amqp-send to republish).
 */

try {
  const incoming = msg.payload || {};

  // Accept body as object or JSON string - normalize to an object first
  let body = incoming.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body);
    } catch (e) {
      body = { data: body };
    }
  } else if (body === undefined || body === null || typeof body !== 'object') {
    body = {};
  }

  const appProps = incoming.application_properties || {};

  // Field-agnostic - copies whatever keys application_properties has, no hardcoding
  const header = {};
  for (const key in appProps) {
    if (appProps.hasOwnProperty(key)) {
      header[key] = appProps[key];
    }
  }

  // If the real AMQP correlation-id property is set and isn't already covered
  // by an application_properties field (matched generically, same pattern as
  // setupAmqpProperties.js), add it into the header too.
  const hasCorrelationField = Object.keys(header).some(
    (key) => /^correlation[-_]?id$/i.test(key)
  );
  if (!hasCorrelationField && incoming.correlation_id !== undefined) {
    header.correlationId = incoming.correlation_id;
  }

  body.header = header;

  // amqp-send contract: body and application_properties nested inside
  // msg.payload as sibling keys, matching what setupAmqpProperties.js produces.
  msg.payload = {
    body,
    application_properties: appProps,
    ...(incoming.correlation_id !== undefined && { correlation_id: incoming.correlation_id }),
    ...(incoming.content_type !== undefined && { content_type: incoming.content_type })
  };

  // Drop leftover intermediate fields (e.g. from an upstream prepareBody.js) -
  // their data now lives in msg.payload, keeping them around is pure duplication.
  delete msg.rawBody;
  delete msg.parsedBody;
  delete msg.bodyParsed;

  node.status({
    fill: 'green',
    shape: 'dot',
    text: `Header set (${Object.keys(header).length} fields)`
  });
  return msg;
} catch (error) {
  node.status({ fill: 'red', shape: 'dot', text: 'Error' });
  msg.error = `Failed to copy properties to header: ${error.message}`;
  return msg;
}
