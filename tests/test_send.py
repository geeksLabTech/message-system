from message_system.message_system import MessageSystem
import threading

stop_flag = threading.Event()


def send_funct(ms):
    while not stop_flag.is_set():
        ms.send()


def test_send_message():

    ms = MessageSystem()

    ms.add_to_send("test")

    data = None

    send_thread = threading.Thread(
        target=send_funct, args=(ms,))
    send_thread.start()

    data = ms.receive('test')

    stop_flag.set()

    assert not data is None
    assert data


stop_flag = threading.Event()


def send_heartbeat_funct(ms):
    while not stop_flag.is_set():
        ms.send_heartbeat()


def test_send_message_heartbeat():

    ms = MessageSystem()

    ms.add_to_send("test")

    data = None

    send_thread = threading.Thread(
        target=send_heartbeat_funct, args=(ms,))
    send_thread.start()

    data = ms.receive('test')

    stop_flag.set()

    assert not data is None
