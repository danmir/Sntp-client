import datetime
import socket
import struct
import time

import ntp_packet
from ntp_packet import NTP, NTPPacket, NTPException


class SNTPClient:

    """SNTP client session."""

    def __init__(self):
        """Constructor."""
        pass

    def request(self, host, version=4, port='ntp', timeout=5):
        """
        Query a SNTP server.

        :param host: server name/address
        :param version: SNTP version to use
        :param port: server port
        :param timeout: timeout on socket operations
        :returns: NTPStats object
        """
        # lookup server address
        addrinfo = socket.getaddrinfo(host, port)[0]
        sockaddr = addrinfo[4]

        # create the socket
        # print(sockaddr)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.settimeout(timeout)

            # create the request packet - mode 3 is client
            query_packet = NTPPacket(mode=3, version=version,
                                     tx_timestamp=ntp_packet.system_to_ntp_time(time.time()))

            # send the request
            s.sendto(query_packet.to_data(), sockaddr)

            # wait for the response - check the source address
            src_addr = None,
            while src_addr[0] != sockaddr[0]:
                response_packet, src_addr = s.recvfrom(256)

            # build the destination timestamp
            dest_timestamp = ntp_packet.system_to_ntp_time(time.time())
        except socket.timeout:
            raise NTPException("No response received from %s." % host)
        finally:
            s.close()

        # construct corresponding packet
        sntp_packet = NTPPacket()
        sntp_packet.from_data(response_packet)
        sntp_packet.dest_timestamp = dest_timestamp

        print("Offset: ", (((sntp_packet.recv_timestamp - sntp_packet.orig_timestamp) +
                            (sntp_packet.tx_timestamp - sntp_packet.dest_timestamp)) / 2))
        print("Round trip: ", ((sntp_packet.dest_timestamp - sntp_packet.orig_timestamp) -
                               (sntp_packet.tx_timestamp - sntp_packet.recv_timestamp)))

        return sntp_packet


def main():
    p = SNTPClient()
    p.request("192.168.1.119", 4, 123)

if __name__ == '__main__':
    main()
