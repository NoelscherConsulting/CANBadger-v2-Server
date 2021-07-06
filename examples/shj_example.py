#####################################################################################
# CanBadger Security Hijack Example                                                 #
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

import socket
import struct
import time
import sys

from canbadger_api.ethernet_message import EthernetMessage, EthernetMessageType, ActionType
from canbadger_api.security_hijack_message import SecurityHijackMessage
from canbadger_api.security_hijack_response import SecurityHijackResponse
from canbadger.canbadger_defines import CanbadgerInterface, CANFormat, AddressingType

#NODE_IP = "10.0.0.113"
NODE_IP="10.0.0.123"
PORT = 13371
tport = 15555  # we will get msgs from cb after connect here
sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind(('0.0.0.0', tport))
sock.sendto(b'\x04' + b'\x00' + struct.pack('<I', 4) + struct.pack('<I', tport) + b'\x00',
            (NODE_IP, PORT))
# receive ack
ack = sock.recvfrom(128)
print(ack)

msg = SecurityHijackMessage(0x7e0, 0x7e8, 2, 2)
sock.sendto(msg.serialize(), (NODE_IP, PORT))

# receive shj response
response = sock.recvfrom(128)
eth = EthernetMessage.unserialize(response[0], unpack_data=True)
shj_response = SecurityHijackResponse(eth.data)

print(shj_response.success, shj_response.session_level)
