#####################################################################################
# CanBadger CanFrame                                                                #
# Copyright (c) 2020 Noelscher Consulting GmbH                                      #
#                                                                                   #
# Permission is hereby granted, free of charge, to any person obtaining a copy      #
# of this software and associated documentation files (the "Software"), to deal     #
# in the Software without restriction, including without limitation the rights      #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell         #
# copies of the Software, and to permit persons to whom the Software is             #
# furnished to do so, subject to the following conditions:                          #
#                                                                                   #
# The above copyright notice and this permission notice shall be included in        #
# all copies or substantial portions of the Software.                               #
#                                                                                   #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR        #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,          #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE       #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER            #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,     #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN         #
# THE SOFTWARE.                                                                     #
#####################################################################################

# class to hold frames send from the canbadger
# can be constructed with values in a parser class or parsed from raw input bytes

# use enum for the CAN Formats
from enum import Enum

# used for parsing bytes
import struct

# used to implement sorting capabilities for CanFormat
from functools import total_ordering


# used to represent the format of the frame
@total_ordering
class CanFormat(Enum):
    Standard = 0
    Extended = 1
    CAN_FD = 2
    UNIDENTIFIED = 3

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


# class to hold frame send from the canbadger
# can be used in can_parser instead of just shoving the data into a struct
class CanFrame:
    def __init__(self, interface_number: int, frame_format: CanFormat, timestamp: int, frame_id: int,
                 interface_speed: int, data_length: int, frame_payload: bytes):
        self.interface_number = interface_number
        self.frame_format = frame_format
        self.timestamp = timestamp
        self.frame_id = frame_id
        self.interface_speed = interface_speed
        self.data_length = data_length
        self.frame_payload = frame_payload
        self.model_counter = 0
        self.item_container = None

        self.check_validity()

    # checks for sensible values in all fields
    # raises an ArgumentException if we have nonsense in a certain field
    def check_validity(self):

        # interface number can currently only hold 1 or 2
        # but as the data is never really used and the field will become obsolete
        # we dont test for it

        # check for recognised CAN Format
        if not isinstance(self.frame_format, CanFormat) or self.frame_format == CanFormat.UNIDENTIFIED:
            raise AttributeError("Error parsing frame format!")

        # timestamp from canbadger is in micro_seconds from the start of logging/mitm/etc
        # so the value cant the negative but can hold any value up to 4 byte unsigned (4.294.967.295‬)
        if self.timestamp < 0 or self.timestamp > 4294967295:
            raise AttributeError("Error parsing timestamp!")

        # frame id for standard has 11 Bit (0x0 - 0x7FF), extended and can_fd have 29 Bit id (0x0 - 0x 1FFFFFFF)
        if self.frame_format == CanFormat.Standard:
            if self.frame_id < 0 or self.frame_id > 0x7FF:
                raise AttributeError("{} is an invalid id for standard CAN frame!".format(self.frame_id))

        else:
            if self.frame_id < 0 or self.frame_id > 0x1FFFFFFF:
                raise AttributeError("{} is an invalid id for CAN frame!".format(self.frame_id))

        # can speed (in bit/s) is also dependent on the format
        # as is the max payload length (8 byte standard & extended, 64 byte can_fd)
        if self.frame_format == CanFormat.CAN_FD:
            if self.interface_speed < 0 or self.interface_speed > 12000000:
                raise AttributeError("{} is an invalid speed for CAN FD interface!".format(self.interface_speed))
            if self.data_length < 0 or self.data_length > 64:
                raise AttributeError("{} is an invalid payload length for CAN FD!".format(self.data_length))
        else:
            # max speed is 1Mbit/s, we test for 2 as some controllers can send faster
            if self.interface_speed < 0 or self.interface_speed > 2000000:
                raise AttributeError("{} is an invalid spped for CAN interface!".format(self.interface_speed))
            if self.data_length < 0 or self.data_length > 8:
                raise AttributeError("{} is an invalid payload length for CAN Frame!".format(self.data_length))

        # check if the length of the payload actually matches the given value
        if self.data_length != len(self.frame_payload):
            raise AttributeError("Given length {} and actual length {} don't match!".format(self.data_length,
                                                                                            len(self.frame_payload)))

        return True

    # exposes information on how to handle this object as a row in qt
    @classmethod
    def column_representation(cls):
        return ["model_counter", "frame_id", "frame_payload", "interface_number", "!model!.hash_get"]

    @classmethod
    def from_raw_canbadger_bytes(cls, raw_input: bytes):
        unpack_can_header = struct.Struct('<BIIIB').unpack

        # extract related bytes from raw
        protocol_byte, timestamp, frame_id, if_speed, data_length = unpack_can_header(raw_input[:14])

        # get interface number and used frame format from first byte and reverse frame_id endianess
        if_no, frame_format = cls.parse_protocol_byte(protocol_byte)
        frame_id = cls.reverse_endianess_32(frame_id)

        return cls(if_no, frame_format, timestamp, frame_id, if_speed, data_length, raw_input[14:])

    # frame identifier will be received in little_endian, we want to reverse it to store it as an integer
    @classmethod
    def reverse_endianess_32(cls, x):
        return (((x << 24) & 0xFF000000) |
                ((x << 8) & 0x00FF0000) |
                ((x >> 8) & 0x0000FF00) |
                ((x >> 24) & 0x000000FF))

    # can frame type and used interface are both encoded in the first byte the of received data
    # LSB1 is interface 1, LSB2 is interface 2, LSB3 and 4 are CAN/KLINE (unused so far),
    # LSB5 & LSB6 are Standard or Extended format, we expect every pair to be mutually exclusive
    @classmethod
    def parse_protocol_byte(cls, pbyte: int):
        frame_format = 0
        if pbyte & 0x10 > 0:
            frame_format = CanFormat.Standard
        elif pbyte & 0x20 > 0:
            if frame_format == CanFormat.Standard:
                raise AttributeError("multiple can formats checked in protocol byte!")
            frame_format = CanFormat.Extended
        else:
            frame_format = CanFormat.UNIDENTIFIED

        interface_no = 0
        if pbyte & 0x01 > 0:
            interface_no = 1
        elif pbyte & 0x02 > 0:
            if interface_no == 1:
                raise AttributeError("multiple interfaces checked in protocol byte!")
            interface_no = 2
        else:
            interface_no = 0

        return interface_no, frame_format

    # methods to test for format if you dont want to use the enum in the code using CanFrame
    def is_standard(self):
        if self.frame_format == CanFormat.Standard:
            return True
        else:
            return False

    def is_extended(self):
        if self.frame_format == CanFormat.Extended:
            return True
        else:
            return False

    def is_canfd(self):
        if self.frame_format == CanFormat.CAN_FD:
            return True
        else:
            return False

    # returns the value associated with the given column (defined in the column_representation of this class)
    def get_column(self, column):
        # check column bounds
        if column < 0 or column >= len(self.__class__.column_representation()):
            return None

        # determine what to retrieve
        target = self.__class__.column_representation()[column]

        # if the target contains the !model! identifier, the data is not stored in the frame
        # but instead requires retrieval from the model
        if "!model!" in target:
            # we call the targeted model function with our frames hash
            value = getattr(self.item_container.model, target[8:])(self.get_compare_hash())
        elif "!item!" in target:
            # we retrieve the items value
            value = getattr(self.item_container, target[7:])
        else:
            # return the value of the attribute defined in the column_representation of this class
            value = getattr(self, target)

        if type(value) is not bytes:
            return str(value)
        else:
            # return a string representation of the bytes object that does not totally destroy the data...
            return value.hex()

    # used by the model to save the order of frames when logging etc.
    def set_counter(self, counter: int):
        self.model_counter = counter

    # returns a hash that's derived from some of the attributes
    # used to count multiples of frames
    def get_compare_hash(self):
        # currently we use payload, format and sender id to produce the hash
        return hash((self.frame_payload, self.frame_format, self.frame_id))

    # return attributes in a list
    def list_representation(self):
        list_rep = [self.timestamp, "CAN" + str(self.interface_number), self.frame_format.name, self.interface_speed,
                    hex(self.frame_id), self.data_length]

        for byte in self.frame_payload:
            list_rep.append(hex(byte))
        return list_rep
