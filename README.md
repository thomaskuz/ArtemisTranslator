# Artemis Protocol Converter & Message Transformer

AMQP 1.0 messaging with Apache Artemis and Python Qpid Proton.

## Prerequisites

- Docker & Docker Compose
- Python 3.7+
- `python-qpid-proton` library

## Quick Start

### 1. Start Artemis
```bash
docker-compose up -d
```

Access web UI: **http://localhost:8161** (admin/admin)

### 2. Create Queue in Artemis Console

1. Go to **Artemis → Addresses**
2. Create Address: `test.queue`
3. Click on address → Create Queue: `test.queue`

### 3. Set Up Python
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Send Your First Message

**Terminal 1: Listen for messages**
```bash
python consumer_amqp.py
```

**Terminal 2: Send a message**
```bash
python publisher_amqp.py
```

You should see the message flow! ✅

## Scripts

### `publisher_amqp.py`
Sends a single message to Artemis queue and exits.

```bash
python publisher_amqp.py
# Output:
# [✓] Connected to Artemis
# [✓] Sender ready for queue: test.queue
# [✓] Sent: Hello Artemis!
```

### `consumer_amqp.py`
Listens for messages on queue (runs indefinitely).

```bash
python consumer_amqp.py
# Output:
# [✓] Connected to Artemis
# [✓] Listening on queue: test.queue
# [!] Press Ctrl+C to stop
# 
# [✓] Message 1 received:
#     Hello Artemis!
```

## Web UI

**Artemis Console**: http://localhost:8161
- Username: `admin`
- Password: `admin`
- View connections, queues, messages
- Monitor AMQP 1.0 traffic

## Important: Authentication

The scripts use AMQP connection URL with credentials:
```
amqp://admin:admin@localhost:5672
```

This is required for Artemis authentication. Update credentials if you change them.

## Learning

Read [guides/python-basics.md](guides/python-basics.md) to understand:
- Python fundamentals
- How Proton AMQP 1.0 works
- Publisher script explained line-by-line
- Consumer script explained line-by-line

## Configuration

Edit the scripts to change:

**Publisher:**
```python
broker = "amqp://admin:admin@localhost:5672"  # Connection URL
queue = "test.queue"  # Queue name
message = "Hello Artemis!"  # Message content
```

**Consumer:**
```python
broker = "amqp://admin:admin@localhost:5672"  # Connection URL
queue = "test.queue"  # Queue name to listen on
```

## Stopping Services

```bash
docker-compose down
```

Full cleanup (remove data):
```bash
docker-compose down -v
```

## Troubleshooting

**Connection refused?**
- Check Artemis is running: `docker-compose ps`
- Wait 20 seconds for startup
- Check logs: `docker-compose logs artemis`

**Queue doesn't exist?**
- Create it in Artemis web console (Addresses → Create Address)

**Authentication failed?**
- Verify credentials in connection URL
- Check Artemis admin user exists

## AMQP 1.0 Features Used

- ✅ Proton library (official AMQP 1.0)
- ✅ Sender/Receiver links
- ✅ Message persistence
- ✅ Authentication
- ✅ Event-driven callbacks

## Next Steps

- [ ] Modify message content and queue names
- [ ] Add error handling
- [ ] Implement message transformation logic
- [ ] Connect multiple queues
- [ ] Add monitoring/metrics
