"""
important constants and enums for the canbadger
"""

from enum import IntEnum

#####################################################################################
# CanBadger Defines                                                                 #
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

class CanbadgerInterface(IntEnum):
    INTERFACE_1 = 0
    INTERFACE_2 = 1


class CANFormat(IntEnum):
    STANDARD_FORMAT = 0
    EXTENDED_FORMAT = 1
    ANY_FORMAT = 2


class AddressingType(IntEnum):
    """
    Define Standard or Extended UDS Addressing
    """
    STANDARD_ADDRESSING = 0
    EXTENDED_ADDRESSING = 1


class StatusBits(IntEnum):
    SD_ENABLED = 0
    USB_SERIAL_ENABLED = 1
    ETHERNET_ENABLED = 2
    OLED_ENABLED = 3
    KEYBOARD_ENABLED = 4
    LEDS_ENABLED = 5
    KLINE1_INT_ENABLED = 6
    KLINE2_INT_ENABLED = 7
    CAN1_INT_ENABLED = 8
    CAN2_INT_ENABLED = 9
    KLINE_BRIDE_ENABLED = 10
    CAN_BRIDGE_ENABLED = 11
    CAN1_LOGGING = 12
    CAN2_LOGGING = 13
    KLINE1_LOGGING = 14
    KLINE2_LOGGING = 15
    CAN1_STANDARD = 16
    CAN1_EXTENDED = 17
    CAN2_STANDARD = 18
    CAN2_EXTENDED = 19
    CAN1_TO_CAN2_BRIDGE = 20
    CAN2_TO_CAN1_BRIDGE = 21
    KLINE1_TO_KLINE2_BRIDGE = 22
    KLINE2_TO_KLINE1_BRIDGE = 23
    UDS_CAN1_ENABLED = 24
    UDS_CAN2_ENABLED = 25
    CAN1_USE_FULLFRAME = 26
    CAN2_USE_FULLFRAME = 27
    CAN1_MONITOR = 28
    CAN2_MONITOR = 29
