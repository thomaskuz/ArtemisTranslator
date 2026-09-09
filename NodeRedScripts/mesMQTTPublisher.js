// MES MQTT Publisher Function
// Creates MES TrackIn event with proper MQTT metadata
// Input: Trigger message
// Output: msg.payload (JSON) + msg.properties (MQTT metadata)

// Create MES TrackIn payload
const mesPayload = {
  "MES_Data": {
    "specversion": "1.0",
    "type": "imec.mes.trackin",
    "source": "MES",
    "subject": "v1.0/imec/Leuven/Cleanroom/MES/TrackIn",
    "origin": "v1.0/imec/Leuven/Cleanroom/MES",
    "id": "MES-" + new Date().toISOString().split('T')[0].replace(/-/g, '') + "-" + Math.random().toString().substr(2, 8),
    "sequence": "001",
    "time": new Date().toISOString(),
    "datacontenttype": "application/json",
    "dataschema": "https://schemas.imec.be/mes.trackin.v1.json",
    "data": {
      "schemaVersion": "0.1.0",
      "eventType": "TRACKIN",
      "sourceSystem": "MES",
      "sourceCorrelationId": "c3baf6b4-f9a2-41d4-a7d8-91b2c5b6cfd1",
      "sourceEventId": "MES-" + new Date().toISOString().split('T')[0].replace(/-/g, '') + "-00012345",
      "eventTimestamp": new Date().toISOString(),

      "toolName": "GRIND_CMP_Z1",
      "toolState": "TRACKIN",

      "subComponents": ["LOADPORT_1", "CHUCK_A", "PROCESS_MODULE_1"],

      "slotMapContent": [
        "WAFER0001", "WAFER0002", "WAFER0003", "WAFER0004", "WAFER0005",
        "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""
      ],

      "carrierId": "FOUP_000987654",
      "lotName": "LOT" + new Date().toISOString().split('T')[0].replace(/-/g, '') + "001",
      "product": "CMP_PRODUCT_A",
      "productType": "Production",

      "flowName": "CMP_FLOW",
      "module": "GRIND",
      "step": "CMP_PROCESS",

      "uniqueFlowPath": "CMP_FLOW/GRIND/CMP_PROCESS/001",
      "logicalFlowPath": "CMP Flow > Grind > CMP Process",

      "flowRecipe": "C700_TEMP_NCG_GR",
      "lotPriority": 2,
      "lotQuantity": 25,
      "recipeReleaseState": "Released",

      "substrates": [
        "Si", "Si", "Si", "Si", "Si",
        "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""
      ]
    }
  }
};

// Generate message ID for correlation
const msgId = "msgId_" + Math.random().toString().substr(2, 12);

// Set MQTT message payload and topic
msg.payload = mesPayload;
msg.topic = "fromAppToE3";

// MQTT v5 Predefined Properties (protocol-level metadata)
msg.contentType = "application/json";           // Content-Type property
msg.correlationData = msgId;                    // Correlation-Data for linking messages
msg.messageExpiryInterval = 3600;               // Message expires in 1 hour (3600 seconds)
msg.payloadFormatIndicator = 1;                 // 1 = UTF-8 text format

// MQTT v5 User Properties (custom key-value pairs)
// Set as JSON object for NodeRed MQTT Out
msg.userProperties = {
  "action-name": "TRACKIN",
  "application-name": "E3_MES_Integration",    // ← Underscores, not spaces!
  "source": "MES",
  "status": "200"
};

// Alternative: If using Artemis AMQP Out, set application_properties instead
// msg.applicationProperties = {
//   "action-name": "TRACKIN",
//   "application-name": "E3 MES Integration",
//   "source": "MES",
//   "status": "200"
// };

return msg;
