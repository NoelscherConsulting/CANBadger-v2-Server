#####################################################################################
# CanBadger Can Parser                                                              #
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

from datatypes import CanFrame, CanFormat
import struct


class CanParser:
    def __init__(self):
        # compile the structs beforehand
        self.unpack_unpack_can_header = struct.Struct('>BIIIB').unpack

    def reverse_endianess_32(self, x):
        return (((x << 24) & 0xFF000000) |
                ((x << 8) & 0x00FF0000) |
                ((x >> 8) & 0x0000FF00) |
                ((x >> 24) & 0x000000FF))

    ##
    # data is supposed to be a bytes object
    def parseSingleFrame(self, data: bytes):
        busno, timestamp, arbid, speed, length = self.unpack_unpack_can_header(data[:14])

        payload = data[14:14 + length]
        return {'id': arbid, 'payload': payload, 'busno': busno, 'timestamp': timestamp}

    # parse the data into a can frame
    def parseToCanFrame(self, data: bytes):
        pbyte, timestamp, arbid, speed, length = self.unpack_unpack_can_header(data[:14])
        payload = data[14:14 + length]
        interface_no, frame_format = CanFrame.parse_protocol_byte(pbyte)
        return CanFrame(interface_no, frame_format, timestamp, arbid, speed, length, payload)

    # returns a CanFrame from all the arguments given
    def constructCanFrame(self, arbid, data_len, data, timestamp=None, speed=None, interface=None):
        if speed is None:
            speed = 0
        if timestamp is None:
            timestamp = 0
        if interface is None:
            interface = 1

        return CanFrame(interface, CanFormat.Standard, timestamp, arbid, speed, data_len, data)

