# Fill the fields of sntp header according to rfc4330 (4. Message format)
#  "This format is identical to the NTP message format described in RFC 1305,
#  with the exception of the Reference Identifier field described below.  For
#  SNTP client messages, most of these fields are zero or initialized"
#  with pre-specified data.
# Use some functions from ntplib

import datetime
import socket
import struct
import time


class NTPException(Exception):

    """Exception raised by this module."""
    pass


class NTP:

    """Helper class defining constants."""

    _SYSTEM_EPOCH = datetime.date(*time.gmtime(0)[0:3])
    """system epoch"""
    _NTP_EPOCH = datetime.date(1900, 1, 1)
    """NTP epoch"""
    NTP_DELTA = (_SYSTEM_EPOCH - _NTP_EPOCH).days * 24 * 3600
    """delta between system and NTP time"""


class NTPPacket:

    """
    NTP packet class.
    """

    _PACKET_FORMAT = "!B B B b 11I"
    # spaces will be ignored
    """packet format to pack/unpack"""

    def __init__(self, version=4, mode=4, tx_timestamp=0):
        """
        Constructor.
        :param version: NTP version. Default Sntp v4
        :param mode: packet mode (client, server) Defaulf 4 - server
        :param tx_timestamp: acket transmit timestamp
        :return:
        """
        self.leap = 0
        """leap second indicator"""
        self.version = version
        """version"""
        self.mode = mode
        """mode"""
        self.stratum = 0
        """stratum"""
        self.poll = 0
        """poll interval"""
        self.precision = 0
        """precision"""
        self.root_delay = 0
        """root delay"""
        self.root_dispersion = 0
        """root dispersion"""
        self.ref_id = 0
        """reference clock identifier"""
        self.ref_timestamp = 0
        """reference timestamp"""
        self.orig_timestamp = 0
        self.orig_timestamp_high = 0
        self.orig_timestamp_low = 0
        """originate timestamp"""
        self.recv_timestamp = 0
        """receive timestamp"""
        self.tx_timestamp = tx_timestamp
        self.tx_timestamp_high = 0
        self.tx_timestamp_low = 0
        """tansmit timestamp"""

    def to_data(self):
        """
        Convert this NTPPacket to a buffer that can be sent over a socket.
        :return: buffer representing this packet
        :raises: NTPException -- in case of invalid field
        """
        try:
            packed = struct.pack(NTPPacket._PACKET_FORMAT,
                                 (self.leap << 6 |
                                  self.version << 3 | self.mode),
                                 self.stratum,
                                 self.poll,
                                 self.precision,
                                 _to_int(self.root_delay) << 16 | _to_frac(
                                     self.root_delay, 16),
                                 _to_int(self.root_dispersion) << 16 |
                                 _to_frac(self.root_dispersion, 16),
                                 self.ref_id,
                                 _to_int(self.ref_timestamp),
                                 _to_frac(self.ref_timestamp),
                                 self.orig_timestamp_high,
                                 self.orig_timestamp_low,
                                 _to_int(self.recv_timestamp),
                                 _to_frac(self.recv_timestamp),
                                 _to_int(self.tx_timestamp),
                                 _to_frac(self.tx_timestamp))
        except struct.error:
            raise NTPException("Invalid NTP packet fields.")
        return packed

    def from_data(self, data):
        """
        Populate this instance from a NTP packet payload received from
        the network.

        :param data: buffer payload
        :raises: NTPException -- in case of invalid packet format
        """
        try:
            unpacked = struct.unpack(NTPPacket._PACKET_FORMAT,
                                     data[0:struct.calcsize(NTPPacket._PACKET_FORMAT)])
        except struct.error:
            raise NTPException("Invalid NTP packet.")

        self.leap = unpacked[0] >> 6 & 0x3
        self.version = unpacked[0] >> 3 & 0x7
        self.mode = unpacked[0] & 0x7
        self.stratum = unpacked[1]
        self.poll = unpacked[2]
        self.precision = unpacked[3]
        self.root_delay = float(unpacked[4]) / 2**16
        self.root_dispersion = float(unpacked[5]) / 2**16
        self.ref_id = unpacked[6]
        self.ref_timestamp = _to_time(unpacked[7], unpacked[8])
        self.orig_timestamp = _to_time(unpacked[9], unpacked[10])
        self.recv_timestamp = _to_time(unpacked[11], unpacked[12])
        self.tx_timestamp = _to_time(unpacked[13], unpacked[14])
        self.tx_timestamp_high = unpacked[13]
        self.tx_timestamp_low = unpacked[14]

    def GetTxTimeStamp(self):
        return (self.tx_timestamp_high, self.tx_timestamp_low)

    def SetOriginTimeStamp(self, high, low):
        self.orig_timestamp_high = high
        self.orig_timestamp_low = low


def _to_int(timestamp):
    """Return the integral part of a timestamp.

    Parameters:
    timestamp -- NTP timestamp

    Retuns:
    integral part
    """
    return int(timestamp)


def _to_frac(timestamp, n=32):
    """Return the fractional part of a timestamp.

    Parameters:
    timestamp -- NTP timestamp
    n         -- number of bits of the fractional part

    Retuns:
    fractional part
    """
    return int(abs(timestamp - _to_int(timestamp)) * 2**n)


def _to_time(integ, frac, n=32):
    """Return a timestamp from an integral and fractional part.

    Parameters:
    integ -- integral part
    frac  -- fractional part
    n     -- number of bits of the fractional part

    Retuns:
    timestamp
    """
    return integ + float(frac) / 2**n


def ntp_to_system_time(timestamp):
    """Convert a NTP time to system time.

    Parameters:
    timestamp -- timestamp in NTP time

    Returns:
    corresponding system time
    """
    return timestamp - NTP.NTP_DELTA


def system_to_ntp_time(timestamp):
    """Convert a system time to a NTP time.

    Parameters:
    timestamp -- timestamp in system time

    Returns:
    corresponding NTP time
    """
    return timestamp + NTP.NTP_DELTA
