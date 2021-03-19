#####################################################################################
# CanBadger SocketCanConnection                                                     #
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

# this is used to wrap a socketcansource for usage in the QT application
# modeled after the node_connection handling the QT signals
# while the socketcansource handles receiving data

from PySide2.QtCore import Signal, Slot, QObject
import socket
from multiprocessing import Queue
from queue import Empty
from connections.socketcan_source import SocketCanSource


class SocketCanConnection(QObject):
    connectionSucceeded = Signal()
    connectionFailed = Signal(str)
    nodeDisconnected = Signal(dict)

    def __init__(self, node):
        super(SocketCanConnection, self).__init__()
        self.node = node
        self.isConnected = False
        self.socket = None
        self.data_queue = Queue()
        self.signal_queue = Queue()
        self.command_queue = Queue()
        self.logger_process = None

    def onRun(self):
        self.socket = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        interface = self.node["id"]
        try:
            self.socket.bind((interface, ))
            self.isConnected = True
            self.connectionSucceeded.emit()
        except OSError:
            self.connectionFailed.emit(interface)

    def runCanlogger(self):
        if self.isConnected:
            self.logger_process = SocketCanSource(self.socket, command_queue=self.command_queue,
                                                  message_queue=self.data_queue)
            self.logger_process.start()

    def stopCurrentAction(self):
        if self.logger_process is not None:
            self.command_queue.put("kys")

            # drain the queue
            drain_queue = Queue()
            while True:
                try:
                    drain_queue.put(self.data_queue.get_nowait())
                except Empty:
                    break
            self.data_queue = drain_queue

            self.logger_process.join()
            print("logger process joined!")
            self.logger_process = None

    @Slot()
    def resetConnection(self):
        if self.isConnected:
            self.isConnected = False
            self.nodeDisconnected.emit(self.node)
            self.cleanup()

    def cleanup(self):
        self.isConnected = False
        if self.socket is not None:
            self.socket.close()


