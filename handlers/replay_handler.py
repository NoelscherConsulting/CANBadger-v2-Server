#####################################################################################
# CanBadger Replay Handler                                                          #
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

from PySide2.QtWidgets import QAbstractItemView
from PySide2.QtCore import QModelIndex, Qt, QItemSelectionModel
import time

from connections.node_connection import *
from helpers import *
from models import CanLoggerTableModel
from canbadger_messages.ethernet_message import EthernetMessageType, ActionType


class ReplayHandler(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(ReplayHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.model = CanLoggerTableModel(self.mainwindow.replayFramesTableView)
        self.currentRowModelIndex = None
        self.selectionModel = None
        self.replayList = None

    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.replayRemoveFrameBtn.clicked.connect(self.onRemoveFrame)
        self.mainwindow.startReplayBtn.clicked.connect(self.onStartReplay)
        self.mainwindow.replayFrameIdLineEdit.textEdited.connect(self.onFrameIdEdited)
        self.mainwindow.replayPayloadLineEdit.textEdited.connect(self.onFramePayloadEdited)
        self.mainwindow.replayCountLineEdit.textEdited.connect(self.onFrameCountEdited)
        self.mainwindow.replayInterfaceSelection.activated.connect(self.onFrameInterfaceEdited)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)
        self.mainwindow.addReplayFrameBtn.clicked.connect(self.onAddReplayFrameClicked)
        self.mainwindow.replayMoveUpBtn.clicked.connect(self.onMoveUpFrame)
        self.mainwindow.replayMoveDownBtn.clicked.connect(self.onMoveDownFrame)

    @Slot()
    def setup_gui(self):
        self.mainwindow.replayFramesTableView.setModel(self.model)
        self.mainwindow.replayFramesTableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mainwindow.replayFramesTableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.selectionModel = self.mainwindow.replayFramesTableView.selectionModel()
        self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)


    @Slot(QModelIndex, QModelIndex)
    def onCurrentRowChanged(self, current, prev):
        if self.currentRowModelIndex is None:
            self.setEditingEnabled(True)
        if current is None:
            self.setEditingEnabled(False)
            self.mainwindow.replayFrameIdLineEdit.setText('')
            self.mainwindow.replayPayloadLineEdit.setText('')
            self.mainwindow.replayCountLineEdit.setText('')
        else:
            # update values
            self.setEditingEnabled(True)
            frame = self.model.getFrame(current)
            self.mainwindow.replayCountLineEdit.setText(str(frame[0]))
            self.mainwindow.replayFrameIdLineEdit.setText(hex(frame[1]))
            self.mainwindow.replayPayloadLineEdit.setText(''.join('{:02x}'.format(x) for x in frame[2]))
            self.mainwindow.replayInterfaceSelection.setCurrentIndex(
                self.mainwindow.replayInterfaceSelection.findText(str(frame[3])))
        self.currentRowModelIndex = current


    def setEditingEnabled(self, value):
        self.mainwindow.replayCountLineEdit.setEnabled(value)
        self.mainwindow.replayFrameIdLineEdit.setEnabled(value)
        self.mainwindow.replayPayloadLineEdit.setEnabled(value)
        self.mainwindow.replayRemoveFrameBtn.setEnabled(value)

    @Slot()
    def onRemoveFrame(self):
        self.model.removeFrame(self.currentRowModelIndex)

    @Slot()
    def onStartReplay(self):
        if self.mainwindow.selectedNode is None or self.mainwindow.selectedNode["version"] == "socket_can":
            return

        if len(self.model.getFrames()) < 1:
            return

        connection = self.mainwindow.selectedNode['connection']

        # preformat and put frames into queue
        formatted_frames = []
        for frame in self.model.getFrames():
            interface = struct.pack('B', frame[3])
            id = struct.pack('I', frame[1])
            frame_payload_raw = frame[2]
            count = frame[0]

            if len(frame_payload_raw) == 0 or count == 0:
                continue

            payload = struct.pack("%ds" % len(frame_payload_raw), frame_payload_raw)
            formatted_frames.append((count, interface + id + payload))

        # connect signals to trigger next replay on ACK
        # also connect NACK, we want to send later frames even on NACK (can be due to interface etc.)
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.sendNextReplay)
        connection.nackReceived.connect(self.sendNextReplay)

        self.replayList = formatted_frames

        self.sendNextReplay()

    @Slot()
    def sendNextReplay(self):
        connection = self.mainwindow.selectedNode['connection']
        if self.replayList is None or len(self.replayList) == 0:
            # nothing left to send, disconnect signals
            self.replayList = None
            gracefullyDisconnectSignal(connection.ackReceived)
            gracefullyDisconnectSignal(connection.nackReceived)
            return

        cnt, command = self.replayList[0]

        # send one replay command
        connection.sendMessage(
            EthernetMessage(EthernetMessageType.ACTION, ActionType.START_REPLAY, len(command), command))

        if cnt > 1:
            if len(self.replayList) > 1:
                self.replayList = [(cnt - 1, command)] + self.replayList[1:]
            else:
                self.replayList = [(cnt - 1, command)]
        else:
            if len(self.replayList) > 1:
                self.replayList = self.replayList[1:]
            else:
                # last command was sent, set replayList to None and wait for ACK
                self.replayList = None

    @Slot(str)
    def onFrameIdEdited(self, text):
        if self.currentRowModelIndex is None:
            return
        if len(text)<=2:
            self.model.updateFrame(self.currentRowModelIndex, {'ID': 0})
        else:
            self.model.updateFrame(self.currentRowModelIndex, {'ID': int(text, 16)})

    @Slot(str)
    def onFramePayloadEdited(self, text):
        try:
            self.model.updateFrame(self.currentRowModelIndex, {'Payload': bytes.fromhex(text)})
        except ValueError:
            pass # dont update

    @Slot(int)
    def onFrameInterfaceEdited(self):
        if self.currentRowModelIndex is None:
            return

        inf = int(self.mainwindow.replayInterfaceSelection.currentText(), 10)
        self.model.updateFrame(self.currentRowModelIndex, {'Interface': inf})

    @Slot(str)
    def onFrameCountEdited(self, text):
        if self.currentRowModelIndex is None:
            return
        try:
            cnt = int(text)
        except ValueError:
            cnt = 0
        self.model.updateFrame(self.currentRowModelIndex, {'Frame Count': cnt})

    @Slot(list)
    def onAddReplayFrame(self, frame):
        self.model.addFrame(frame)

    @Slot()
    def onAddReplayFrameClicked(self):
        if self.mainwindow.selectedNode is not None:
            self.model.addFrame([0, 0, b"", 1])
            #self.selectionModel.select(self.model.createIndex(self.model.rowCount() - 1, 0),
            #                           QItemSelectionModel.SelectCurrent)

    @Slot(int)
    def onTabChanged(self, index):
        if index == 1:
            self.mainwindow.tabWidget_2.tabBar().setTabTextColor(1, Qt.black)

    @Slot(object, dict)
    def onSelectedNodeChanged(self, previous, current):
        if current is not None:
            if previous is not None:
                if "replay" not in previous:
                    previous["replay"] = {}
                previous["replay"]["model"] = self.model
            if "replay" not in current:
                current["replay"] = {}
                current["replay"]["model"] = CanLoggerTableModel()
            self.model = current["replay"]["model"]
            self.mainwindow.replayFramesTableView.setModel(self.model)
            self.selectionModel = self.mainwindow.replayFramesTableView.selectionModel()
            gracefullyDisconnectSignal(self.selectionModel.currentRowChanged)
            self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)

        self.setEditingEnabled(False)

    @Slot()
    def onMoveUpFrame(self):
        if self.currentRowModelIndex is None or self.currentRowModelIndex.row() < 1:
            return

        if self.model.moveUpFrame(self.currentRowModelIndex):
            newindex = self.model.createIndex(self.currentRowModelIndex.row() - 1, 0)
            self.selectionModel.select(newindex, QItemSelectionModel.SelectCurrent)
            self.currentRowModelIndex = newindex

    @Slot()
    def onMoveDownFrame(self):
        if len(self.model.can_data) < 1:
            return

        if self.model.moveDownFrame(self.currentRowModelIndex):
            newindex = self.model.createIndex(self.currentRowModelIndex.row() + 1, 0)
            self.selectionModel.select(newindex, QItemSelectionModel.SelectCurrent)
            self.currentRowModelIndex = newindex

