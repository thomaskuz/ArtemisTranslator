/**
 * Debug Inject - Sample AMQP Message with Properties (NodeRed)
 *
 * Test helper for copyPropertiesToHeader.js. Wire an Inject node into this
 * Function node to simulate a message as it would arrive from amqp-recv
 * (node-red-contrib-rhea): everything nested under msg.payload, with proper
 * application_properties already set, but no "header" in the body yet.
 *
 * Flow: [Inject] -> [this function] -> [copyPropertiesToHeader.js] -> [Debug]
 *
 * Copy this entire code into a NodeRed Function node, placed after an Inject node.
 */

msg.payload = {
  application_properties: {
    correlationSystem: 'CIRCL_2',
    correlationId: 62,
    publisherSystem: 'FILEMANAGER01',
    messageType: 'FileManagerRequestStatusUpdateMessage',
    messageVersion: '0.2.0'
  },
  correlation_id: '62',
  content_type: 'application/json',

  // Body as it would look coming off amqp-recv - no "header" key yet, that's
  // exactly what copyPropertiesToHeader.js is meant to add back in.
  body: {
    schemaVersion: '0.2.0',
    statusUpdateId: 'af9070b2-ff63-4187-a2b5-f0b3fda793a8',
    eventTime: '2026-08-19T08:50:07.576439806Z',
    sourceSystem: 'CIRCL_2',
    sourceRequestId: '4aeA3etc-fc37-40cb-b9e7-f305512ec4f0',
    fileManagerRequestId: 62,
    status: 'ERROR',
    error: {
      errorCode: 'OTHER_ACTION_ERROR',
      errorCategory: 'EXECUTION',
      message: 'CopyFile failed: File already exists on SMB share and overwrite is disabled: temp/Pool/10'
    },
    metadata: {
      LOT_ID: 'LOT_ID_VALUE',
      RECIPE: 'RECIPE_VALUE',
      TOOL_ID: 'KLA_CIRCLE',
      WAFER_ID: 'WAFER_ID_VALUE'
    }
  }
};

return msg;
