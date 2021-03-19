#####################################################################################
# CanBadger Ethernet Message Format                                                 #
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
from enum import IntEnum

class EthernetMessageType(IntEnum):
    ACK = 0
    NACK = 1
    DATA = 2
    ACTION = 3
    CONNECT = 4
    DEBUG_MSG = 5


class ActionType(IntEnum):
    NO_TYPE = 0
    SETTINGS = 1
    EEPROM_WRITE = 2
    LOG_RAW_CAN_TRAFFIC = 3
    ENABLE_TESTMODE = 4
    STOP_CURRENT_ACTION = 5
    RESET = 6
    START_UDS = 7
    START_TP = 8
    UDS = 9
    TP = 10
    UDS_HIJACK = 11
    MITM = 12
    UPDATE_SD = 13
    DOWNLOAD_FILE = 14
    DELETE_FILE = 15
    RECEIVE_RULES = 16
    ADD_RULE = 17
    ENABLE_MITM_MODE = 18
    START_REPLAY = 19
    RELAY = 20
    LED = 21


header_unpack = struct.Struct('<bbI').unpack


class EthernetMessage:
    def __init__(self, msg_type: EthernetMessageType, action_type: ActionType, data_length: int, data: bytes):
        if type(msg_type) == EthernetMessageType:
            self.msg_type = msg_type
        elif type(msg_type) == str:
            self.msg_type = EthernetMessageType(int(msg_type))
        elif type(msg_type) == int:
            self.msg_type = EthernetMessageType(msg_type)
        else:
            raise NotImplementedError("Invalid argument to EthernetMessage: msg_type")

        if type(action_type) == ActionType:
            self.action_type = action_type
        elif type(action_type) == str:
            self.action_type = ActionType(int(action_type))
        elif type(action_type) == int:
            self.action_type = ActionType(action_type)
        else:
            raise NotImplementedError("Invalid argument to EthernetMessage: action_type")

        self.data_length = data_length
        self.data = data

    def serialize(self) -> bytes:
        if self.data:
            return struct.pack("<BBI%ds" % (self.data_length), self.msg_type, self.action_type, self.data_length, self.data)
        else:
            return struct.pack('<BBI', self.msg_type, self.action_type, self.data_length)

    @staticmethod
    def unserialize(raw_data, unpack_data=False):
        if len(raw_data) < 6:
            raise Exception('ethernet_message.unserialize: Tried to unserialize invalid data!')
        # parse header
        (msg_type, action_type, data_length) = header_unpack(raw_data[:6])
        data = b''
        if unpack_data and len(raw_data[6:]) == data_length:
            data = raw_data[6:]
        return EthernetMessage(EthernetMessageType(msg_type), ActionType(action_type), data_length, data)

    # ACCESSORS
    def getMsgType(self) -> EthernetMessageType:
        return self.msg_type

    def getActionType(self) -> ActionType:
        return self.action_type
