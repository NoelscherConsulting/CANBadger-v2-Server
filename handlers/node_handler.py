#####################################################################################
# CanBadger Node Handler                                                            #
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

from connections.node_connection import *
from connections import SocketCanConnection
from helpers import buttonFeedback
from PySide2.QtCore import QMutex, QTimer
from PySide2.QtNetwork import QUdpSocket, QHostAddress
import datetime


# handle discovery and connection of nodes
class NodeHandler(QObject):

    newNodeDiscovered = Signal(dict)
    nodeConnected = Signal(dict)
    nodeDisconnected = Signal(dict)
    nodeDisappeared = Signal(dict)
    nodeAliveMessage = Signal(dict)
    cleanupDone = Signal()

    threadReady = Signal()

    def __init__(self, mainwindow):
        super(NodeHandler, self).__init__()
        self.visibleNodes = {}
        self.connectedNodes = {}
        self.nodeListMutex = QMutex()
        self.mainwindow = mainwindow

    @Slot()
    def onRun(self):
        # multithreading hack to prevent threading sigsev conditions
        # all the stuff should be executed in this threads event loop
        # if we do stuff here, the thread context could be different
        self.threadReady.connect(self.onThreadReady)
        self.threadReady.emit()

    @Slot()
    def onThreadReady(self):
        self.udpSocket = QUdpSocket(self)
        #self.udpSocket.bind(13370, QUdpSocket.ShareAddress)
        self.udpSocket.bind(13370, QUdpSocket.ReuseAddressHint)
        self.udpSocket.readyRead.connect(self.onSocketReadyRead)

        # check every second
        self.disconnectTimer = QTimer(self)
        self.disconnectTimer.moveToThread(self.thread())
        self.disconnectTimer.timeout.connect(self.onDisconnectTimerFire)
        self.disconnectTimer.start(100)


    @Slot()
    def onSocketReadyRead(self):
        msg = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())
        if msg[0][0:2] == "CB":
            msg_split = msg[0].split('|')
            device_id = msg_split[1].data().decode('ascii')
            device_version = msg_split[2].data().decode('ascii')
            now = datetime.datetime.now()
            ip = QHostAddress(msg[1].toIPv4Address()).toString()
            device = {"id": device_id, "version": device_version, "ip": ip, "last_seen": now}
            self.nodeListMutex.lock()
            if (device_id not in self.connectedNodes.keys()) and \
                    (device_id not in self.visibleNodes.keys()):
                self.visibleNodes[device_id] = device
                self.newNodeDiscovered.emit(device)
                print(f"discovered {device_id}")
            # update timestamps for known visible/connected devices
            if device_id in self.visibleNodes.keys():
                self.visibleNodes[device_id]["last_seen"] = now
                self.nodeAliveMessage.emit(self.visibleNodes[device_id])
            if device_id in self.connectedNodes.keys():
                self.connectedNodes[device_id]["last_seen"] = now
                self.nodeAliveMessage.emit(self.connectedNodes[device_id])
            self.nodeListMutex.unlock()

    @Slot(str)
    def onSocketCanDiscovered(self, vcan):
        now = datetime.datetime.now()
        device = {"id": vcan, "version": "socket_can", "ip": None, "last_seen": now}
        self.nodeListMutex.lock()
        if (vcan not in self.connectedNodes.keys()) and \
                (vcan not in self.visibleNodes.keys()):
            self.visibleNodes[vcan] = device
            self.newNodeDiscovered.emit(device)
        if vcan in self.visibleNodes.keys():
            self.visibleNodes[vcan]["last_seen"] = now
            self.nodeAliveMessage.emit(self.visibleNodes[vcan])
        if vcan in self.connectedNodes.keys():
            self.connectedNodes[vcan]["last_seen"] = now
            self.nodeAliveMessage.emit(self.connectedNodes[vcan])
        self.nodeListMutex.unlock()


    @Slot()
    def onDisconnectTimerFire(self):
        now = datetime.datetime.now()
        self.nodeListMutex.lock()
        ids_to_delete = []
        for id, node in self.visibleNodes.items():
            # check time difference
            if (now - node["last_seen"]) > datetime.timedelta(seconds=6):
                ids_to_delete.append(id)
                self.nodeDisappeared.emit(node)
        for id in ids_to_delete:
            del self.visibleNodes[id]
        ids_to_delete = []
        for id, node in self.connectedNodes.items():
            # check time difference
            if (now - node["last_seen"]) > datetime.timedelta(seconds=10):
                ids_to_delete.append(id)
                self.nodeDisconnected.emit(node)
        for id in ids_to_delete:
            # check for running connection process
            if self.connectedNodes[id]["connection"].isConnected:
                self.connectedNodes[id]["connection"].resetConnection()
            del self.connectedNodes[id]
        self.nodeListMutex.unlock()

    @Slot(dict)
    def onConnectToNode(self, node):
        print(f"Node handler creating connection to {node['id']}.")
        if ("connection" not in node.keys() or node["connection"] is None) and node["ip"] is not None:
            # start a connection to a canbadger
            con = NodeConnection(node)
            node["connection"] = con
            con.connectionSucceeded.connect(self.onConnectionSucceeded)
            con.connectionFailed.connect(self.onConnectionFailed)
            con.newSettingsData.connect(self.mainwindow.onSettingsReceived)
            self.mainwindow.exiting.connect(con.resetConnection)

            con.onRun()

        elif ("connection" not in node.keys() or node["connection"] is None) and node["ip"] is None:
            # start a socketCan connection
            con = SocketCanConnection(node)
            node["connection"] = con
            con.connectionSucceeded.connect(self.onConnectionSucceeded)
            con.connectionFailed.connect(self.onConnectionFailed)
            self.mainwindow.exiting.connect(con.cleanup)

            con.onRun()

    @Slot()
    def onConnectionSucceeded(self):
        node_connection = self.sender()
        node = node_connection.node

        self.nodeListMutex.lock()
        if node["id"] in self.visibleNodes.keys():
            del self.visibleNodes[node["id"]]
        self.connectedNodes[node["id"]] = node
        self.nodeListMutex.unlock()
        self.nodeConnected.emit(node)
        node_connection.nodeDisconnected.connect(self.onDisconnectNode)

    @Slot()
    def onConnectionFailed(self):
        # signal red
        buttonFeedback(False, self.mainwindow.interfaceSelection)


    @Slot(dict)
    def onDisconnectNode(self, node):
        # reset connection and terminate thread
        if "connection" in node.keys():
            node["connection"].resetConnection()
        if "thread" in node.keys():
            node["thread"].exit()
            pass

        # delete the node from dicts
        self.nodeListMutex.lock()
        if node["id"] in self.connectedNodes:
            del self.connectedNodes[node["id"]]
        if node["id"] in self.visibleNodes:
            del self.visibleNodes[node["id"]]
        self.nodeListMutex.unlock()
        self.nodeDisconnected.emit(node)

    @Slot(str, str)
    def onIDChange(self, old, new):
        self.nodeListMutex.lock()
        if old in self.connectedNodes:
            self.connectedNodes[new] = self.connectedNodes[old]
            del self.connectedNodes[old]
        if old in self.visibleNodes:
            self.visibleNodes[new] = self.visibleNodes[old]
            del self.visibleNodes[old]
        self.nodeListMutex.unlock()


    @Slot()
    def onExiting(self):
        self.disconnectTimer.stop()
        self.udpSocket.close()
        self.cleanupDone.emit()
