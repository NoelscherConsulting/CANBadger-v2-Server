#####################################################################################
# CanBadger UDS Response                                                            #
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

import struct
from canbadger_messages.ethernet_message import EthernetMessage, EthernetMessageType, ActionType

class UdsResponse(object):
    def __init__(self, data: bytes):
        """parses eth_msg.data and sets all internal fields of the response"""
        self.data = data
        self.sid, self.is_positive_reply, self.payload_len = struct.unpack('<H?I', self.data[:7])
        self.payload = self.data[7:]

    @staticmethod
    def make_response(sid, is_positive_reply, payload) -> bytes:
        data = struct.pack('<H?I', sid, is_positive_reply, len(payload)) + payload
        eth = EthernetMessage(EthernetMessageType.DATA, ActionType.NO_TYPE, len(data), data)
        return eth.serialize()
