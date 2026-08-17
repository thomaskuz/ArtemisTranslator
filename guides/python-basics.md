# Python Basics Guide - AMQP 1.0 Publisher & Consumer

This guide explains the Python scripts line-by-line so you learn both Python and AMQP 1.0 with Proton.

## Table of Contents

1. [Python Fundamentals](#python-fundamentals)
2. [How Publisher Works](#how-publisher-works)
3. [How Consumer Works](#how-consumer-works)
4. [Running the Scripts](#running-the-scripts)
5. [Key Concepts](#key-concepts)

---

## Python Fundamentals

### Comments
```python
# This is a comment - Python ignores it
"""
This is a multi-line comment/docstring
Used to document what code does
"""
```

### Variables
```python
name = "Alice"          # Text (string)
age = 25                # Number (integer)
price = 19.99           # Decimal number (float)
is_active = True        # Boolean (True or False)
```

### Functions
```python
def greet(name):
    """This function says hello"""
    print(f"Hello, {name}!")

greet("Alice")  # Call the function
# Output: Hello, Alice!
```

### Classes
A class is a blueprint for creating objects:

```python
class Car:
    def __init__(self, color):
        self.color = color  # Store the color
    
    def describe(self):
        print(f"This car is {self.color}")

my_car = Car("red")  # Create an instance
my_car.describe()    # Call a method
# Output: This car is red
```

### Inheritance
When a class inherits from another, it gets all its functionality:

```python
class Animal:
    def speak(self):
        print("Some sound")

class Dog(Animal):  # Dog inherits from Animal
    def speak(self):
        print("Woof!")

dog = Dog()
dog.speak()  # "Woof!"
```

### Imports
```python
from proton import Message  # Import one thing
from proton.handlers import MessagingHandler  # Import from nested module
from proton.reactor import Container  # Import another thing
import sys  # Import entire module
```

---

## How Publisher Works

### Complete Script

```python
#!/usr/bin/env python3
"""
Simple AMQP 1.0 Publisher - Sends messages to Artemis
"""

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys

class Publisher(MessagingHandler):
    """A class that handles sending messages"""

    def __init__(self, url, queue, message_text):
        super(Publisher, self).__init__()
        self.url = url
        self.queue = queue
        self.message_text = message_text
        self.sent = False

    def on_start(self, event):
        """Called when container starts"""
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        event.container.create_sender(event.connection, self.queue)

    def on_link_opened(self, event):
        """Called when sender link opens"""
        if event.sender:
            print(f"[✓] Sender ready for queue: {self.queue}")

    def on_sendable(self, event):
        """Called when we can send a message"""
        if not self.sent and event.sender:
            self.sent = True
            msg = Message(body=self.message_text)
            event.sender.send(msg)
            print(f"[✓] Sent: {self.message_text}")
            event.connection.close()

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"
    message = "Hello Artemis!"

    try:
        handler = Publisher(broker, queue, message)
        container = Container(handler)
        container.run()
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Line-by-Line Breakdown

#### Imports (Lines 4-7)
```python
from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys
```

**What it does:** Load libraries needed for AMQP 1.0
- **Message**: Class for creating AMQP messages
- **MessagingHandler**: Base class for handling AMQP events
- **Container**: Manages the AMQP connection and event loop
- **sys**: Access system functions (exit codes, stderr)

#### Class Definition (Line 10)
```python
class Publisher(MessagingHandler):
    """A class that handles sending messages"""
```

**What it does:** 
- Creates a new class called `Publisher`
- **Inheritance**: `Publisher(MessagingHandler)` means Publisher inherits from MessagingHandler
- Gets all of MessagingHandler's functionality plus adds our own

#### Constructor (Lines 12-17)
```python
def __init__(self, url, queue, message_text):
    super(Publisher, self).__init__()
    self.url = url
    self.queue = queue
    self.message_text = message_text
    self.sent = False
```

**What it does:**
- `__init__`: Special method that runs when creating a new Publisher
- `super().__init__()`: Call parent class's constructor
- `self.url = url`: Store the URL as an instance variable
- `self.sent = False`: Track whether message has been sent

#### On Start Method (Lines 19-21)
```python
def on_start(self, event):
    """Called when container starts"""
    event.container.connect(self.url)
```

**What it does:**
- `on_start`: **Callback** - runs automatically when the container starts
- `event.container.connect()`: Establish connection to Artemis using the URL
- URL format: `amqp://admin:admin@localhost:5672`
  - `admin:admin` = credentials
  - `localhost:5672` = broker address and AMQP port

#### On Connection Opened (Lines 23-26)
```python
def on_connection_opened(self, event):
    """Called when connection to broker opens"""
    print(f"[✓] Connected to Artemis")
    event.container.create_sender(event.connection, self.queue)
```

**What it does:**
- `on_connection_opened`: **Callback** - runs when connection to Artemis succeeds
- `create_sender()`: Create an AMQP sender (the thing that sends messages to the queue)
- Sender is tied to a specific queue (self.queue)

#### On Link Opened (Lines 28-31)
```python
def on_link_opened(self, event):
    """Called when sender link opens"""
    if event.sender:
        print(f"[✓] Sender ready for queue: {self.queue}")
```

**What it does:**
- `on_link_opened`: **Callback** - runs when the sender link is ready
- `if event.sender`: Check if this is a sender link (not a receiver)
- At this point, we're ready to send messages

#### On Sendable (Lines 33-41)
```python
def on_sendable(self, event):
    """Called when we can send a message"""
    if not self.sent and event.sender:
        self.sent = True
        msg = Message(body=self.message_text)
        event.sender.send(msg)
        print(f"[✓] Sent: {self.message_text}")
        event.connection.close()
```

**What it does:**
- `on_sendable`: **Callback** - runs when the sender has credit (can send)
- `if not self.sent`: Only send once (prevent duplicate sends)
- `Message(body=...)`: Create an AMQP message with text content
- `event.sender.send(msg)`: Send the message to the queue
- `event.connection.close()`: Close the connection after sending

#### On Error (Lines 43-46)
```python
def on_error(self, event):
    """Called on error"""
    print(f"[✗] Error: {event.condition}", file=sys.stderr)
    sys.exit(1)
```

**What it does:**
- `on_error`: **Callback** - runs if something goes wrong
- `file=sys.stderr`: Print to error stream (not standard output)
- `sys.exit(1)`: Exit with error code 1

#### Main Function (Lines 48-59)
```python
def main():
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"
    message = "Hello Artemis!"

    try:
        handler = Publisher(broker, queue, message)
        container = Container(handler)
        container.run()
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)
```

**What it does:**
- `main()`: Entry point - runs when script starts
- **Variable assignment**: Store configuration
- `try/except`: Error handling - catch any problems
- `Publisher(...)`: Create a new Publisher instance
- `Container(publisher)`: Wrap it in a Container
- `container.run()`: Start the connection and begin event loop

#### Script Entry Point (Lines 61-62)
```python
if __name__ == "__main__":
    main()
```

**What it does:**
- Only run if this file is executed directly (not imported)
- `main()`: Call the main function

---

## How Consumer Works

### Complete Script

```python
#!/usr/bin/env python3
"""
Simple AMQP 1.0 Consumer - Receives messages from Artemis
"""

from proton.handlers import MessagingHandler
from proton.reactor import Container
import sys

class Consumer(MessagingHandler):
    """A class that handles receiving messages"""

    def __init__(self, url, queue):
        super(Consumer, self).__init__()
        self.url = url
        self.queue = queue
        self.received_count = 0

    def on_start(self, event):
        """Called when container starts"""
        event.container.connect(self.url)

    def on_connection_opened(self, event):
        """Called when connection to broker opens"""
        print(f"[✓] Connected to Artemis")
        event.container.create_receiver(event.connection, self.queue)

    def on_link_opened(self, event):
        """Called when receiver link opens"""
        if event.receiver:
            print(f"[✓] Listening on queue: {self.queue}")
            print(f"[!] Press Ctrl+C to stop\n")

    def on_message(self, event):
        """Called when a message arrives"""
        self.received_count += 1
        message_body = event.message.body
        print(f"[✓] Message {self.received_count} received:")
        print(f"    {message_body}\n")

    def on_error(self, event):
        """Called on error"""
        print(f"[✗] Error: {event.condition}", file=sys.stderr)
        sys.exit(1)

def main():
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"

    try:
        handler = Consumer(broker, queue)
        container = Container(handler)
        container.run()
    except KeyboardInterrupt:
        print(f"\n[!] Stopped by user")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Key Differences from Publisher

#### Constructor (Lines 12-17)
```python
def __init__(self, url, queue):
    super(Consumer, self).__init__()
    self.url = url
    self.queue = queue
    self.received_count = 0
```

- `self.received_count = 0`: Track how many messages we've received

#### On Connection Opened (Lines 23-26)
```python
def on_connection_opened(self, event):
    print(f"[✓] Connected to Artemis")
    event.container.create_receiver(event.connection, self.queue)
```

- `create_receiver()`: Instead of `create_sender()`, create a receiver (listens for messages)

#### On Link Opened (Lines 28-32)
```python
def on_link_opened(self, event):
    if event.receiver:
        print(f"[✓] Listening on queue: {self.queue}")
        print(f"[!] Press Ctrl+C to stop\n")
```

- `if event.receiver`: Check if this is a receiver link (not a sender)

#### On Message (Lines 34-39) - UNIQUE TO CONSUMER
```python
def on_message(self, event):
    """Called when a message arrives"""
    self.received_count += 1
    message_body = event.message.body
    print(f"[✓] Message {self.received_count} received:")
    print(f"    {message_body}\n")
```

**What it does:**
- `on_message`: **Callback** - runs every time a message arrives
- `self.received_count += 1`: Increment counter (add 1)
  - Same as: `self.received_count = self.received_count + 1`
- `event.message.body`: Extract the actual message content
- Print what we received

#### Main Function (Lines 48-59)
```python
def main():
    broker = "amqp://admin:admin@localhost:5672"
    queue = "test.queue"

    try:
        handler = Consumer(broker, queue)
        container = Container(handler)
        container.run()
    except KeyboardInterrupt:
        print(f"\n[!] Stopped by user")
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        sys.exit(1)
```

- `except KeyboardInterrupt`: Catch Ctrl+C gracefully
- `container.run()`: Runs forever (keeps listening for messages)

---

## Running the Scripts

### Install Dependencies
```bash
pip install python-qpid-proton
```

### Terminal 1: Start Consumer
```bash
python consumer.py
```

Output:
```
[✓] Connected to Artemis
[✓] Listening on queue: test.queue
[!] Press Ctrl+C to stop
```

Consumer is now waiting for messages.

### Terminal 2: Send a Message
```bash
python publisher.py
```

Output:
```
[✓] Connected to Artemis
[✓] Sender ready for queue: test.queue
[✓] Sent: Hello Artemis!
```

Publisher sends one message and exits.

### What Appears in Terminal 1
```
[✓] Connected to Artemis
[✓] Listening on queue: test.queue
[!] Press Ctrl+C to stop

[✓] Message 1 received:
    Hello Artemis!
```

---

## Key Python Concepts

### Callbacks
Callbacks are functions that run automatically when something happens:

```python
def on_message(self, event):
    # This runs automatically when a message arrives
    # You DON'T call this yourself
    print("Got a message!")
```

The Proton library calls these methods for you when events occur.

### String Formatting (F-Strings)
```python
name = "Alice"
age = 25
message = f"My name is {name} and I'm {age} years old"
# "My name is Alice and I'm 25 years old"
```

The `f` prefix lets you insert variables with `{}`.

### Operator: +=
```python
count = 0
count += 1  # Same as: count = count + 1
print(count)  # Output: 1
```

### Exception Handling (Try/Except)
```python
try:
    # Try to do something
    result = 10 / 0  # This will fail
except ZeroDivisionError:
    # If it fails, do this
    print("Can't divide by zero!")
except Exception as e:
    # Catch any other error
    print(f"Error: {e}")
```

### AMQP Connection URL
```
amqp://admin:admin@localhost:5672
 │    │    │      │        │
 │    │    │      │        └─ Port
 │    │    │      └─ Hostname
 │    │    └─ Password
 │    └─ Username
 └─ Protocol (AMQP 1.0)
```

---

## Proton AMQP 1.0 Event Flow

### Publisher
```
on_start()
    ↓
connect() [async]
    ↓
on_connection_opened()
    ↓
create_sender() [async]
    ↓
on_link_opened()
    ↓
on_sendable()
    ↓
send() + close()
```

### Consumer
```
on_start()
    ↓
connect() [async]
    ↓
on_connection_opened()
    ↓
create_receiver() [async]
    ↓
on_link_opened()
    ↓
(wait for messages...)
    ↓
on_message() [called for each message]
    ↓
(repeat until Ctrl+C)
```

---

## Next Steps

1. Run both scripts and watch them communicate
2. Modify the message text in publisher.py
3. Create different queues in Artemis console
4. Try sending multiple messages
5. Add custom headers to messages
6. Build message transformation logic
7. Read Proton documentation for advanced features

Good luck learning Python and AMQP 1.0! 🚀
