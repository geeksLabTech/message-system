import socket
import struct
import time
import threading
from socket import SHUT_RDWR
import sys
import logging
import netifaces as ni


# Create a file handler
file_handler = logging.FileHandler("log_file.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)


class MessageSystem:

    def __init__(self, host_ip=None, broadcast_addr=None):
        # if fixed host or broadcast addr set in here

        self.host_ip = host_ip
        self.broadcast_addr = broadcast_addr

        # list of pending to send data and pending to receive
        # send is started as an empty listm and recieve with a "hear all" to recieve all broadcasts
        self.pendig_send = []
        self.pendig_receive = [{"port": "0.0.0.0", "times": -1}]

    @staticmethod
    def get_ips():
        """Get a list of all NICs with information

        Returns:
            List[Dict]: a list with the information (ip, mask, broadcast addr and more) of each of the available NICs in the PC
        """

        # Get all network interfaces
        interfaces = ni.interfaces()

        # Sort the interfaces by preference: LAN, WLAN, and localhost
        interfaces = sorted(
            interfaces, key=lambda x: ("wl" in x, "eth" in x, "en" in x), reverse=True
        )

        ips = []
        for interface in interfaces:
            try:
                # Get the IP address for the current interface

                ip = ni.ifaddresses(interface)[ni.AF_INET][0]
                if ip:
                    ips.append(ip)
            except Exception as e:
                # Investigate why this fails so much
                # logger = logging.getLogger(__name__)
                # logger.warning(f"The following exception was throwed in get_ips {e}")
                pass

        return ips

    def _mc_send(self, hostip: str, mcgrpip: str, mcport: int, msgbuf):
        """Send a message over a port and ip

        Args:
            hostip (str): IP of the sender PC in the NIC on wich the broadcast is being sent
            mcgrpip (str): Multicast IP of the sender PC
            mcport (int): multicast port on wich the broadcast is going to be sent
            msgbuf (bytes): message to send
        """
        # This creates a UDP socket
        sender = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP,
            fileno=None,
        )
        # This defines a multicast end point, that is a pair
        #   (multicast group ip address, send-to port nubmer)

        if not 'broadcast' in hostip:
            return
        mcgrp = (hostip['broadcast'], mcport)

        # This defines how many hops a multicast datagram can travel.
        # The IP_MULTICAST_TTL's default value is 1 unless we set it otherwise.
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set the IP_MULTICAST_LOOP option to False to ignore local messages
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        # This defines to which network interface (NIC) is responsible for
        # transmitting the multicast datagram; otherwise, the socket
        # uses the default interface (ifindex = 1 if loopback is 0)
        # If we wish to transmit the datagram to multiple NICs, we
        # ought to create a socket for each NIC.
        sender.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(
                hostip["addr"])
        )

        # Transmit the datagram in the buffer
        # print("sending", msgbuf, mcgrp)
        sender.sendto(msgbuf, mcgrp)

        # release the socket resources
        sender.close()

    @staticmethod
    def is_socket_open(sock: socket.socket):
        """Verify if a socket is still opened

        Args:
            sock (socket.socket): socket to check

        Returns:
            bool: True if open, False if not
        """
        try:
            sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return True  # Socket is open
        except socket.error:
            return False  # Socket is closed

    def stop_listening(self, sock: socket.socket, duration=0.5):
        """Close a socket after a given time

        Args:
            sock (socket.socket): socket to close
            duration (int, optional): time to wait. Defaults to 3.
        """
        threading.Timer(duration, self.close_sock, [sock]).start()

    @staticmethod
    def close_sock(sock: socket.socket):
        """close a socket the safest way possioble

        Args:
            sock (socket.socket): socket to close
        """        
        # verify if socket is open
        if MessageSystem.is_socket_open(sock):
            logger.debug(f"closing socket, {str(sock)}")
            try:
                # try to prevent peer of the inminent close
                if sys.platform.startswith("linux"):
                    sock.shutdown(SHUT_RDWR)
            except OSError:
                pass
            try:
                # close socket
                sock.close()
            except OSError:
                pass

    def _mc_recv(self, fromnicip:str, mcgrpip:str, mcport:int, time=3):
        """recieve a multicast message from a NIC 

        Args:
            fromnicip (str): NIC info
            mcgrpip (str): Multicast ip
            mcport (int): multicast port
            time (int, optional): time to listen. Defaults to 3.

        Returns:
            (str, bytes, None): message recieved, None if nothing recieved
        """        
        # This creates a UDP socket
        receiver = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP,
            fileno=None,
        )
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set the IP_MULTICAST_LOOP option to False to ignore local messages
        receiver.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        # This configure the socket to receive datagrams sent to this multicast
        # end point, i.e., the pair of
        #   (multicast group ip address, mulcast port number)
        # that must match that of the sender
        # print((mcgrpip, mcport))
        bindaddr = (mcgrpip, mcport)
        logger.debug(f"listening {mcgrpip}, {mcport}")
        receiver.bind(bindaddr)

        # This joins the socket to the intended multicast group. The implications
        # are two. It specifies the intended multicast group identified by the
        # multicast IP address.  This also specifies from which network interface
        # (NIC) the socket receives the datagrams for the intended multicast group.
        # It is important to note that socket.INADDR_ANY means the default network
        # interface in the system (ifindex = 1 if loopback interface present). To
        # receive multicast datagrams from multiple NICs, we ought to create a
        # socket for each NIC. Also note that we identify a NIC by its assigned IP
        # address.
        if fromnicip == "0.0.0.0":
            struct.pack("=4sl", socket.inet_aton(mcgrpip), socket.INADDR_ANY)
        else:
            struct.pack(
                "=4s4s", socket.inet_aton(
                    mcgrpip), socket.inet_aton(fromnicip["addr"])
            )
        # receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # receiver.timeout(5)
        # ready_to_read, _, _ = select.select([receiver], [], [], 10)

        self.stop_listening(receiver, duration=time)
        # receiver.shutdown(1)
        try:
            buf, senderaddr = receiver.recvfrom(1024)
        except OSError:
            return None, None

        msg = buf.decode()
        logger.debug("msg: %s", msg)

        # Release resources
        receiver.close()

        return msg, senderaddr

    def add_to_send(self, msg:str, times=1, dest=None):
        """Add message to the send list

        Args:
            msg (str): message
            times (int, optional): times to resend te data. Defaults to 1.
            dest (_type_, optional): Optional IP of the reciever. Defaults to None.
        """        
        # generate the package to send
        package = {"message": msg, "times": times}

        # if not pre fixed destination set to none
        if dest is None:
            package["ip"] = None
            package["port"] = None

        # append to list
        self.pendig_send.append(package)

    def send(self):
        """iterate over all the pending to send data and send it
        """        
        
        # if not pre fixed ip, get the main ip
        # if self.host_ip is None:
        #     self_host = socket.gethostname()
        #     self.host_ip = socket.gethostbyname(self_host)

        # iterate over all pending data, if ip is none send it in a multicast over all NICS
        for i in self.pendig_send:
            if i["ip"] is None:
                for nic_ip in MessageSystem.get_ips():
                    self._mc_send(
                        nic_ip, self.broadcast_addr, 50001, i["message"].encode(
                        )
                    )

    def send_heartbeat(self):
        """run a thread to send all pending data every 0.3 secs
        """        
        while True:
            try:
                self.send()
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Exception in heartbeat {str(e)}")

                pass

    def receive(self, service_name: str = '', time=3):
        """Recieve data if pending to recieve data, always will hear at least the multicast Proof of server Up

        Args:
            service_name (str, optional): a name to hear only multicasts carrying information opf same service. Defaults to ''.
            time (int, optional): time to listen. Defaults to 3.

        Returns:
            str, None: message recieved if any
        """        
        to_remove = []

        # print("receiving", self.pendig_receive)
        # iterate over all pending to recieve messages 
        for idx, i in enumerate(self.pendig_receive):
            # update remaining recieve attempts
            if i["times"] > 0:
                i["times"] -= 1
                
            logger.info(f"listening in {self.host_ip}")
            # hear messages in every NIC if broadcast address available 
            for nic_ip in MessageSystem.get_ips():
                if "broadcast" in nic_ip:
                    msg, ip = self._mc_recv(
                        nic_ip, nic_ip["broadcast"], 50001, time=time)

                    # if message recieved verify that service matches 
                    if msg is not None and msg.startswith(service_name):
                        logger.info(f">>> Message from {ip}: {msg}\n")
                        msg = msg.removeprefix(service_name + " ")
                        break
        # if some message to recieve has to be removed, remove it
        for i in to_remove:
            self.pendig_receive.pop(i)

        return msg
