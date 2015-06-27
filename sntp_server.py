import datetime
import socket
import struct
import time
import threading
import select
from queue import *

import argparse
import sys

import ntp_packet
from ntp_packet import NTP, NTPPacket

taskQueue = Queue()
stopFlag = False
work_treads_list = []


class RecvThread(threading.Thread):

    def __init__(self, m_socket, lie_offset):
        threading.Thread.__init__(self)
        self.m_socket = m_socket
        self.lie_offset = lie_offset

    def run(self):
        global taskQueue, stopFlag, work_treads_list
        while True:
            if stopFlag:
                print("RecvThread Ended")
                break
            rlist, _, _ = select.select([self.m_socket], [], [], 1)
            if len(rlist) != 0:
                print("Received {} packets".format(len(rlist)))
                for tempSocket in rlist:
                    try:
                        data, addr = tempSocket.recvfrom(1024)
                        recvTimestamp = ntp_packet.system_to_ntp_time(
                            time.time())
                        taskQueue.put((data, addr, recvTimestamp))
                        workThread = WorkThread(self.m_socket, self.lie_offset)
                        work_treads_list.append(workThread)
                        workThread.start()

                    except socket.error as msg:
                        print(msg)


class WorkThread(threading.Thread):

    def __init__(self, m_socket, lie_offset):
        threading.Thread.__init__(self)
        self.m_socket = m_socket
        self.lie_offset = lie_offset

    def run(self):
        global taskQueue, stopFlag
        while True:
            if stopFlag:
                print("WorkThread Ended")
                break
            try:
                data, addr, recvTimestamp = taskQueue.get(timeout=1)
                recvPacket = NTPPacket()
                recvPacket.from_data(data)

                # Server mode - 4 and SNTP v4
                sendPacket = NTPPacket(version=4, mode=4)
                # According to rfc4330 most fields == 0
                # it is already set in NTPPacket constructor

                # Timestamp Name          ID   When Generated
                # ------------------------------------------------------------
                # Originate Timestamp     T1   time request sent by client
                # Receive Timestamp       T2   time request received by server
                # Transmit Timestamp      T3   time reply sent by server
                # Destination Timestamp   T4   time reply received by client

                timeStamp_high, timeStamp_low = recvPacket.GetTxTimeStamp()
                sendPacket.SetOriginTimeStamp(timeStamp_high, timeStamp_low)
                # Simulate that we have different time on server
                sendPacket.recv_timestamp = recvTimestamp - self.lie_offset
                sendPacket.tx_timestamp = ntp_packet.system_to_ntp_time(
                    time.time() - self.lie_offset)
                # Dummy info to be a correct sntp packet
                sendPacket.stratum = 2
                sendPacket.ref_timestamp = recvTimestamp - 5
                sendPacket.poll = 10
                # sendPacket.precision = 2
                # sendPacket.root_delay = 1
                # sendPacket.root_dispersion = 1
                # sendPacket.ref_id = 1809582983  # ip 107.220.11.135

                # sendPacket = b"\x24\x02\x03\xee\x00\x00\x00\x37\x00\x00\x05\x0f\x6b\xdc\x0b\x87\xd8\xe7\x2f\xa6\x1a\xb4\xc9\x72\xd8\xe7\x30\x27\x66\x15\xdb\x33\xd8\xe7\x30\x26\x02\xe6\xcb\x21\xd8\xe7\x30\x26\x02\xeb\x94\xac"
                self.m_socket.sendto(sendPacket.to_data(), addr)
                print("Sended to {}:{}".format(addr[0], addr[1]))
            except Empty:
                continue


def main():
    global taskQueue, stopFlag, work_treads_list
    parser = argparse.ArgumentParser(
        description='Sntp server that lies on given offset')
    parser.add_argument(
        '--lie_offset', '-lo', required=True, type=float, help="Enter offset to lie on :)")
    namespace = parser.parse_args(sys.argv[1:])

    listenIp = "0.0.0.0"
    listenPort = 123  # For test used 1234
    # Because I have ntpd running on Mac on port 123
    # On Win 8.1 all work ok
    m_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    m_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # m_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    m_socket.bind((listenIp, listenPort))
    print("local socket: ", m_socket.getsockname())
    recvThread = RecvThread(m_socket, namespace.lie_offset)
    recvThread.start()

    while True:
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("Exiting...")
            stopFlag = True
            recvThread.join()  # block until all tasks are done
            map(lambda x: x.join(), work_treads_list)
            m_socket.close()
            print("Exited")
            break
        except exception as e:
            print(e)

if __name__ == '__main__':
    main()
