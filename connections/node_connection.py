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

from PySide2.QtCore import Signal, Slot, QObject, QByteArray
from PySide2.QtNetwork import QUdpSocket, QHostAddress
import random
import struct
import datetime
from multiprocessing import Queue
from queue import Empty

from canbadger_messages.ethernet_message import EthernetMessage, EthernetMessageType, ActionType
from connections.canbadger_source import CanbadgerSource


# handles connection to a single CanBadger
class NodeConnection(QObject):
    connectionSucceeded = Signal()
    connectionFailed = Signal(str)
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
        self.port = random.randint(10000, 13372)
        # TODO: we need a dict of to-be-acked messages so we now what got sent and what didnt
        self.waitForAck = False  # indicates whether there is a pending ACK
        self.testMode = False
        self.frameQueue = []
        self.actionSocket = None
        self.dataSocket = None
        self.data_queue = Queue()  # use this for data-heavy message passing instead of Qt Signals
        self.signal_queue = Queue()
        self.command_queue = Queue()
        self.logger_process = None

    def onRun(self):
        # create sockets for every channel
        # action socket for sending stuff
        self.actionSocket = QUdpSocket()
        # data socket for receiving stuff
        self.dataSocket = QUdpSocket()
        if not self.dataSocket.bind(self.port, QUdpSocket.ReuseAddressHint):
            # reconnect on failure, use other port
            self.port = random.randint(10000, 13372)
            self.threadReady.emit()
            return
        self.dataSocket.readyRead.connect(self.onDataSocketReadyRead)

        self.tryConnect()

    def tryConnect(self):
        # try to initiate connection
        self.actionSocket.writeDatagram(b'\x04' + b'\x00' + struct.pack('<I', 4) +
                                        struct.pack('<I', self.port) + b'\x00', QHostAddress(self.node["ip"]), 13371)

    def updateSettings(self, settings):
        for key, value in settings.items():
            if len(key) > 127:
                print("ERROR: key %s is too long! Max Length: 127 bytes" % (key))
                continue
            if len(value) > 255:
                print("ERROR: value of %s is too long! Max Length: 255 bytes" % (key))
                continue
            if ';' in value:
                print("ERROR: value of %s is invalid: no semicolons allowed!" % (key))
                continue

            # update settings msg should look like: 3|0|key|value\NULLBYTE
            keyval_str = ("%s;%s" % (key, value)).encode('ascii')
            self.actionSocket.writeDatagram(EthernetMessage(EthernetMessageType.ACTION, ActionType.SETTINGS, len(keyval_str), keyval_str).serialize(),
                                            QHostAddress(self.node["ip"]), 13371)
            self.waitForAck = True

    def enableTestmode(self):
        ethMsg = EthernetMessage(EthernetMessageType.ACTION, ActionType.ENABLE_TESTMODE, 0, "")
        self.actionSocket.writeDatagram(ethMsg.serialize(), QHostAddress(self.node["ip"]), 13371)
        self.testMode = True
        self.waitForAck = True

    def sendEthernetMessage(self, msg: EthernetMessage, waitForAck=False):
        self.actionSocket.writeDatagram(msg.serialize(), QHostAddress(self.node["ip"]), 13371)
        self.waitForAck = waitForAck

    def runCanlogger(self, bridge_mode=False):
        self.logger_process = CanbadgerSource(self.node["ip"], command_queue=self.command_queue,
                                              signal_queue=self.signal_queue, message_queue=self.data_queue)
        self.logger_process.start()

    def stopCurrentAction(self):
        if self.logger_process is not None:
            self.command_queue.put("kys")

            # drain the queue
            while not self.data_queue.empty():
                try:
                    self.data_queue.get_nowait()
                except Empty:
                    break

            # join the logger process
            self.logger_process.join()
            print("logger process joined!")
            self.logger_process = None
        else:
            ethMsg = EthernetMessage(EthernetMessageType.ACTION, ActionType.STOP_CURRENT_ACTION, 0, "")
            self.actionSocket.writeDatagram(ethMsg.serialize(), QHostAddress(self.node["ip"]), 13371)
            self.waitForAck = True

    # expects integer ids, not hex strings
    def startTP(self, module_id, channel_negot_id):
        payload = struct.pack("<II", module_id, channel_negot_id)
        self.actionSocket.writeDatagram(EthernetMessage(EthernetMessageType.ACTION, ActionType.START_TP, len(payload),
                                                        payload).serialize(), QHostAddress(self.node["ip"]), 13371)
        self.waitForAck = True

    def callUDSFunction(self, function_id):
        self.actionSocket.writeDatagram(EthernetMessage(EthernetMessageType.ACTION, ActionType.UDS, 1, struct.pack('>B', function_id)).serialize(),
                                        QHostAddress(self.node["ip"]), 13371)
        self.waitForAck = True

    def callTPFunction(self, function_id):
        self.actionSocket.writeDatagram(EthernetMessage(EthernetMessageType.ACTION, ActionType.TP, 1, struct.pack('>B', function_id)).serialize(),
                                        QHostAddress(self.node["ip"]), 13371)
        self.waitForAck = True

    def sendMessage(self, msg):
        self.actionSocket.writeDatagram(msg.serialize(), QHostAddress(self.node["ip"]), 13371)

    def fillFrameQueue(self, frames):
        self.frameQueue = frames

    @Slot()
    def onDataSocketReadyRead(self):
        # update last seen
        self.node["last_seen"] = datetime.datetime.now()
        pending_size = self.dataSocket.pendingDatagramSize()
        msg_data = self.dataSocket.readDatagram(pending_size)[0].data()
        ethMsg = EthernetMessage.unserialize(msg_data, unpack_data=True)
        msg_type = ethMsg.getMsgType()
        if not self.isConnected:
            # ack is 0
            if msg_type == EthernetMessageType.ACK or msg_type == EthernetMessageType.DEBUG_MSG:
                self.isConnected = True
                self.connectionSucceeded.emit()

                # request the settings from the canbadger
                self.actionSocket.writeDatagram(b'\x03' + b'\x01' + struct.pack('<I', 0), QHostAddress(self.node["ip"]),
                                                13371)
            else:
                self.tryConnect()
        else:
            if self.testMode:
                if msg_type == EthernetMessageType.DATA:
                    # emit data signal
                    self.newTestDataMessage.emit(ethMsg.data)
            else:
                if msg_type == EthernetMessageType.DATA:
                    if not ethMsg.getActionType() == ActionType.SETTINGS:
                        # received  data
                        self.newDataMessage.emit(ethMsg.data)
                    else:
                        # received the canbadgers settings
                        self.newSettingsData.emit(ethMsg.data)
                elif msg_type == EthernetMessageType.DEBUG_MSG:
                    self.newDebugMessage.emit(ethMsg.data)
                elif msg_type == EthernetMessageType.ACK:
                    self.waitForAck = False
                    self.ackReceived.emit()
                elif msg_type == EthernetMessageType.NACK:
                    self.waitForAck = False
                    self.nackReceived.emit()
                else:
                    print(f"discarding unknown message {msg_data}")

    @Slot()
    def resetConnection(self):
        if self.isConnected:
            self.actionSocket.writeDatagram(EthernetMessage(EthernetMessageType.ACTION, ActionType.RESET, 0, "").serialize(),
                                            QHostAddress(self.node["ip"]), 13371)
            self.isConnected = False
            self.cleanup()
            print(f"Node connection to {self.node['id']} reset!")

    @Slot()
    def cleanup(self):
        try:
            if self.actionSocket is not None:
                self.actionSocket.close()
        except RuntimeError:
            pass
        try:
            if self.dataSocket is not None:
                self.dataSocket.close()
        except RuntimeError:
            pass