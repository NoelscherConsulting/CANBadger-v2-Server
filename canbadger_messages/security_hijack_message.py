#####################################################################################
# CanBadger SecHijack Message                                                       #
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

class SecurityHijackMessage(EthernetMessage):
    """
    Starts the SecurityHijack operation
    """
    def __init__(self, local_id: int, remote_id: int, security_level: int, session_level: int):
        super(SecurityHijackMessage, self).__init__(EthernetMessageType.ACTION, ActionType.UDS_HIJACK, 0, '')
        self.local_id = local_id
        self.remote_id = remote_id
        self.security_level = security_level
        self.session_level = session_level
        self.data = struct.pack('<IIHH', self.local_id, self.remote_id, self.security_level, self.session_level)
        self.data_length = len(self.data)

    def repack(self):
        """after changing any fields, you have to use this to update the ethMsg data buffer so your changes are applied"""
        self.data = struct.pack('<IIHH', self.local_id, self.remote_id, self.security_level, self.session_level)
        self.data_length = len(self.data)
