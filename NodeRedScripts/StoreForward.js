const MAX_QUEUE = 100;

if (msg.topic === 'control') {
    if (msg.payload === 'open') {
        flow.set('gateOpen', true);
        const queue = flow.get('msgQueue') || [];
        flow.set('msgQueue', []);
        queue.forEach(function(m) { node.send(m); });
    } else if (msg.payload === 'queue') {
        flow.set('gateOpen', false);
    }
    return null;
}

const gateOpen = flow.get('gateOpen') !== false;
if (gateOpen) {
    return msg;
} else {
    const queue = flow.get('msgQueue') || [];
    if (queue.length >= MAX_QUEUE) { queue.shift(); }
    queue.push(msg);
    flow.set('msgQueue', queue);
    return null;
}