# MessageSystem for Multicast communication
## Introduction

This code is a Python package called `MessageSystem` that provides a messaging system using multicast and broadcast. It allows sending and receiving messages over a network using IP addresses and multicast/broadcast ports.

## Installation

To install the `MessageSystem` package, you can use pip. Run the following command in your terminal:

```console
pip install message-system
```

## Basic Usage
Here's an example of how to use the `MessageSystem` package to send and receive messages using multicast and 
broadcast:

### Sender code
Run this code in the PC that needs to send the message.

```python
from message_system.message_system import MessageSystem

# Create an instance of the message system
msg_system = MessageSystem()

# Add a message to the send list
msg_system.add_to_send("Hello, world!")

# Send all pending messages
msg_system.send()
```

### Reciever Code
In another instance (can be a thread in the same program) listen for the messages, default time to listen is 1 second. make sure to have  the listener listening before the message is sent otherwise it wil be lost in the network.

```python
from message_system.message_system import MessageSystem

# Create an instance of the message system
msg_system = MessageSystem()

# Receive messages
message = msg_system.receive()
print(message)  # Output: "Hello, world!"

```

## Additional Features
The MessageSystem package provides several additional features, including:

- Sending and receiving messages using multicast and broadcast.
- Management of pending messages to send and receive.
- Utility to retrieve available IP addresses in the system.

