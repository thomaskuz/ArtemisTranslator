let isConnected = context.get('isConnected') || false;

if (msg.status && msg.status.text) {
    if (msg.status.text === 'node-red:common.status.connected') {
        isConnected = true;
    } else {
        isConnected = false;
    }
    context.set('isConnected', isConnected);
}

const out1 = isConnected
    ? { payload: 'open',  topic: 'control' }
    : { payload: 'queue', topic: 'control' };

const out2 = !isConnected
    ? { payload: 'reconnect', topic: 'reconnect_trigger' }
    : null;

return [out1, out2];