from message_system.message_system import MessageSystem
import socket


def test_get_ip():
    ips = MessageSystem.get_ips()
    assert not ips is None
    assert type(ips) == type([])
    assert len(ips) > 0


def test_socket_open():
    sock = socket.socket(socket.AF_INET)
    sock.bind(('0.0.0.0', 11111))

    assert MessageSystem.is_socket_open(sock) == True

    sock.close()

    assert not MessageSystem.is_socket_open(sock) == True


def test_close_socket():
    sock = socket.socket(socket.AF_INET)
    sock.bind(('0.0.0.0', 11111))

    assert MessageSystem.is_socket_open(sock) == True

    MessageSystem.close_sock(sock)

    assert not MessageSystem.is_socket_open(sock) == True
