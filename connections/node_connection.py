#####################################################################################
# CanBadger NodeConnection                                                          #
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

from PySide2.QtCore import Signal, Slot, QObject, QTimer
import struct
import platform
import subprocess
from os import kill
import signal
from multiprocessing import Queue
from queue import Empty
from libcanbadger import *

# compile struct here to save time
# will unpack 6 bytes of EthernetMessage header
header_unpack = struct.Struct('<bbI').unpack


# handles connection to a single CanBadger
class NodeConnection(QObject):
    connectionSucceeded = Signal()
    connectionFailed = Signal()
    nodeDisconnected = Signal(dict)
    ackReceived = Signal()
    nackReceived = Signal()

    # message signals
    newDebugMessage = Signal(str)
    # is actually QByteArray but this prevents pyqt from doing any conversion
    newDataMessage = Signal(object)
    newSettingsData = Signal(object)
    newTestDataMessage = Signal(str)

    def __init__(self, node):
        super(NodeConnection, self).__init__()
        self.node = node
        self.isConnected = False
        self.port = None
        self.data_queue = Queue()

        self.canbadger = CANBadger(self.node['ip'])

        self.input_timer = QTimer(self)
        self.logging = False

    def onRun(self):
        connected = self.canbadger.connect()

        if connected:
            self.input_timer.timeout.connect(self.checkInput)
            self.input_timer.start(2)
        else:
            self.connectionFailed.emit()


    def sendEthernetMessage(self, msg: EthernetMessage):
        if self.canbadger.get_connection_status() == InterfaceConnectionStatus.Connected:
            self.canbadger.send(msg)

        print(f"sent {msg.action_type.name} command!")

    def runCanlogger(self):
        # set logging so we forward DATA messages to the CanLogger via the data queue
        self.logging = True

        # send command to CANBadger
        self.canbadger.start()

    def stopCurrentAction(self):
        if self.logging:
            self.logging = False

        self.canbadger.stop()

    def checkAcks(self):
        ack = self.canbadger.wait_for_ack(timeout=0.001)
        if ack is None:
            return

        if not self.isConnected:
            # await first ACK from CANbadger and request settings
            if ack:
                self.isConnected = True
                self.connectionSucceeded.emit()
                self.canbadger.request_settings()
            return

        if ack:
            self.ackReceived.emit()
        else:
            self.nackReceived.emit()
        self.checkAcks()

    def checkInput(self):
        eth_msg = self.canbadger.receive()
        if eth_msg == -1:
            self.checkAcks()
            return

        # process received EthernetMessage and trigger signals
        if eth_msg.msg_type == EthernetMessageType.DATA:
            if self.logging:
                # forward data to CanLogger
                self.data_queue.put(eth_msg)
            else:
                if not eth_msg.getActionType() == ActionType.SETTINGS:
                    # received  data
                    self.newDataMessage.emit(eth_msg.data)
                else:
                    # received the canbadgers settings
                    self.newSettingsData.emit(eth_msg.data)
        elif eth_msg.msg_type == EthernetMessageType.DEBUG_MSG:
            self.newDebugMessage.emit(eth_msg.data)
        self.checkInput()

    @Slot()
    def resetConnection(self):
        if self.isConnected:
            self.canbadger.reset()
        self.input_timer.stop()
        self.checkAcks()
        self.checkInput()
        if self.isConnected:
            print(f"Node connection to {self.node['id']} reset!")
        self.isConnected = False

