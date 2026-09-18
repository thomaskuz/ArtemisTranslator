/**
 * MES AMQP-to-MQTT Publisher (NodeRed)
 *
 * Replacement for mesMQTTPublisher.js: instead of a hardcoded demo payload,
 * transforms a REAL incoming AMQP message (from amqp-recv, node-red-contrib-rhea)
 * into the MES TrackIn CloudEvent + MQTT v5 property shape E3 expects.
 *
 * Flow: [amqp-recv] -> [this function] -> [MQTT Out (v5)]
 *
 * Input:  msg.payload                         (from amqp-recv - the whole message,
 *                                              which may itself arrive as a JSON
 *                                              string rather than an object, same
 *                                              as the top-level shape in
 *                                              ExampleMessages/SourceMessages/FM2/AMQPNR_v260819)
 *         msg.payload.application_properties  (field-agnostic - whatever the source system set)
 *         msg.payload.correlation_id          (real AMQP correlation-id)
 *         msg.payload.body                    (the actual MES data - object or JSON string)
 *
 * Output: msg.payload         (mesPayload - the "MES_Data" CloudEvent wrapper)
 *         msg.topic           ("fromAppToE3")
 *         msg.contentType, msg.correlationData, msg.messageExpiryInterval,
 *         msg.payloadFormatIndicator          (MQTT v5 predefined properties)
 *         msg.userProperties                  (AMQP application_properties merged
 *                                              with the static E3-required properties -
 *                                              static ones added LAST, so they win on
 *                                              any key collision)
 *
 * Copy this entire code into a NodeRed Function node, placed after amqp-recv,
 * feeding directly into an MQTT Out node (protocol version 5).
 */

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

try {
  // Normalize msg.payload itself - accept object or JSON string. amqp-recv can
  // hand back the whole message as a stringified JSON blob (same as the
  // top-level shape in ExampleMessages/SourceMessages/FM2/AMQPNR_v260819),
  // not just msg.payload.body.
  let incoming = msg.payload;
  if (typeof incoming === 'string') {
    try {
      incoming = JSON.parse(incoming);
    } catch (e) {
      incoming = {};
    }
  } else if (incoming === undefined || incoming === null || typeof incoming !== 'object') {
    incoming = {};
  }

  // Normalize body - accept object or JSON string (same pattern as
  // copyPropertiesToHeader.js / setupAmqpProperties.js)
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

  // Build the MES CloudEvent envelope - same shape mesMQTTPublisher.js used,
  // but "data" now comes from the real AMQP body instead of hardcoded demo values.
  const mesPayload = {
    "MES_Data": {
      specversion: "1.0",
      type: "imec.mes.trackin",
      source: "MES",
      subject: "v1.0/imec/Leuven/Cleanroom/MES/TrackIn",
      origin: "v1.0/imec/Leuven/Cleanroom/MES",
      id: generateUUID(),
      sequence: "001",
      time: new Date().toISOString(),
      datacontenttype: "application/json",
      dataschema: "https://schemas.imec.be/mes.trackin.v1.json",
      data: body
    }
  };

  msg.payload = mesPayload;
  msg.topic = "fromAppToE3";

  // MQTT v5 predefined properties
  msg.contentType = "application/json";
  if (incoming.correlation_id !== undefined) {
    msg.correlationData = incoming.correlation_id; // required by E3, sourced from the real AMQP correlation-id
  }
  msg.messageExpiryInterval = 3600;
  msg.payloadFormatIndicator = 1;

  // User Properties: AMQP application_properties (field-agnostic - whatever the
  // source system set) merged with the static properties E3 requires. Static
  // ones are spread LAST so they win if a key ever collides with an incoming one.
  msg.userProperties = {
    ...appProps,
    "action-name": "TRACKIN",
    "application-name": "E3_MES_Integration",   // underscores, not spaces!
    "source": "MES",
    "status": "200"
  };

  node.status({ fill: 'green', shape: 'dot', text: 'MES MQTT message ready' });
  return msg;
} catch (error) {
  node.status({ fill: 'red', shape: 'dot', text: 'Error' });
  msg.error = `Failed to build MES MQTT message: ${error.message}`;
  return msg;
}
