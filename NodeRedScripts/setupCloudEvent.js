/**
 * Setup CloudEvent Function (NodeRed)
 *
 * Transforms message into CloudEvents v1.0 format for MQTT publication
 * Expects: msg.parsedBody to be set (from prepareBody function)
 *
 * Input: msg with parsedBody and optional topic
 * Output: msg.payload (stringified CloudEvent) and msg.topic (MQTT topic)
 *
 * Copy this entire code into a NodeRed Function node
 */

// Ensure body is parsed
if (!msg.parsedBody) {
  msg.error = 'parsedBody not set. Run prepareBody first.';
  node.status({ fill: 'red', shape: 'dot', text: 'Missing parsedBody' });
  return msg;
}

try {
  // Generate UUID for event ID
  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  // Determine topic from various sources -> Hier aanpassen
  const defaultTopic = 'v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/QA/File';
  const topic = msg.topic ||
                msg.application_properties?.topic ||
                msg.payload?.topic ||
                defaultTopic;

  // Create CloudEvent (CloudEvents v1.0 format - FASC structure)
  const cloudEvent = {
    specversion: '1.0',
    type: 'imec.event.file_action_status_changed',
    source: 'urn:imec:ot:artemis:file-transfer-server',
    subject: 'v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged',
    id: generateUUID(),
    time: new Date().getTime().toString(),
    datacontenttype: 'application/json',
    dataschema: 'https://schemas.imec.be/imec.event.file_action_status_changed.v1.json',
    data: msg.parsedBody
  };

  // Create clean CloudEvent with data field containing parsed body
  const finalEvent = {
    specversion: '1.0',
    type: 'imec.event.file_action_status_changed',
    source: 'urn:imec:ot:artemis:file-transfer-server',
    subject: 'v1.0/IMEC/Leuven/Cleanroom/Systema/Artemis/Dev/FileActionStatusChanged',
    id: cloudEvent.id,
    time: cloudEvent.time,
    datacontenttype: 'application/json',
    dataschema: 'https://schemas.imec.be/imec.event.file_action_status_changed.v1.json',
    data: msg.parsedBody
  };

  // Create completely clean message with only payload and topic
  const cleanMsg = {
    payload: JSON.stringify(finalEvent),
    topic: topic
  };

  node.status({ fill: 'green', shape: 'dot', text: 'CloudEvent created' });
  return cleanMsg;
} catch (error) {
  node.status({ fill: 'red', shape: 'dot', text: 'CloudEvent error' });
  return {
    payload: JSON.stringify({ error: error.message }),
    topic: topic
  };
}
