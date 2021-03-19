#####################################################################################
# CanBadger UDS RMBA Request Builder                                                #
# Copyright (c) 2021 Noelscher Consulting GmbH                                      #
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

import struct

class ReadMemoryByAddress(object):
    @staticmethod
    def build_request(address, length):
        data = b''
        addrAndFormatId = 1
        if address > 0xFF:
            addrAndFormatId = 2
        if address > 0xFFFF:
            addrAndFormatId = 3
        if address > 0xFFFFFF:
            addrAndFormatId = 4
        if address >= 0x100000000:
            addrAndFormatId = 5

        if length < 0x100:
            addrAndFormatId = addrAndFormatId + 0x10
        elif length > 0xFF and length < 0x10000:
            addrAndFormatId = addrAndFormatId + 0x20
        elif length > 0xFFFF and length < 0x1000000:
            addrAndFormatId = addrAndFormatId + 0x30
        else:
            addrAndFormatId = addrAndFormatId + 0x40

        data += struct.pack('B', addrAndFormatId)
        num_addr_bytes = addrAndFormatId & 0x0F
        num_length_bytes = (addrAndFormatId >> 4) & 0x0F
        addr_copy = address
        length_copy = length
        if num_addr_bytes == 2:
            data += struct.pack('>H', address)
        elif num_addr_bytes == 4:
            data += struct.pack('>I', address)

        if num_length_bytes == 1:
            data += struct.pack('>B', length)
        elif num_length_bytes == 2:
            data += struct.pack('>H', length)
        else:
            data += struct.pack('>I', length)

        return data
