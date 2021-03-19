#####################################################################################
# CanBadger UDS Message                                                             #
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
from canbadger.canbadger_defines import CanbadgerInterface, CANFormat, AddressingType

class StartUdsMessage(EthernetMessage):
    """
    Used to start a diagnostic session
    """
    def __init__(self, interface: CanbadgerInterface, local_id: int, remote_id: int, can_format: CANFormat,
                 enable_padding: bool, padding_byte: bytes, addressing_type: AddressingType, target_diag_session: int):
        super(StartUdsMessage, self).__init__(EthernetMessageType.ACTION, ActionType.START_UDS, 0, '')
        self.interface = interface
        self.local_id = local_id
        self.remote_id = remote_id
        self.can_format = can_format
        self.enable_padding = enable_padding
        self.padding_byte = padding_byte
        self.addressing_type = addressing_type
        self.target_diag_session = target_diag_session
        self.repack()

    def repack(self):
        """after changing any fields, you have to use this to update the ethMsg data buffer so your changes are applied"""
        self.data = struct.pack('<BIIB?BBB', self.interface, self.local_id, self.remote_id, self.can_format,
                                self.enable_padding, self.padding_byte, self.addressing_type, self.target_diag_session)
        self.data_length = len(self.data)


    @staticmethod
    def unpack(data: bytes):
        """unpacks the ethMsg.data part again so we can use it. used for testing"""
        interface, local_id, remote_id, can_format, enable_padding, padding_byte, addressing_type, target_diag_session = struct.unpack('<BIIB?BBB', data)
        return StartUdsMessage(interface, local_id, remote_id, CANFormat(can_format), enable_padding, padding_byte, addressing_type, target_diag_session)
