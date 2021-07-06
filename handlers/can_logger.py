#####################################################################################
# CanBadger Can Logger                                                              #
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

from PySide2.QtWidgets import QAbstractItemView, QFileDialog
import json

from models.can_logger_item_model import *
from helpers.can_parser import *
from models.can_logger_sort_model import *
from delegates.frame_delegate import *
from helpers import *
from libcanbadger import EthernetMessage, EthernetMessageType
from exceptions import UnhandledEthernetMessageException
from queue import Empty
import csv


class CanLogger(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(CanLogger, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.cnt = 0
        self.model = None
        # self.original_frames = [] # used to store the raw frames before filtering
        self.filterById = False
        self.filterAfterNSamples = False
        self.countSortProxy = None
        self.stopped = False
        self.data_timer = QTimer(self)
        self.scroll_timer = QTimer(self)
        self.current_node_connection = None
        self.can_parser = CanParser()
        self.countSortProxy = CanLoggerSortModel(self.mainwindow)
        self.mainwindow.canLogView.setSortingEnabled(True)

    def connect_signals(self):
        self.mainwindow.startCanLoggerBtn.clicked.connect(self.onStartCanLogger)
        self.mainwindow.canLogView.sendToReplay.connect(self.mainwindow.replayHandler.onAddReplayFrame)
        self.mainwindow.canLogView.createRuleForId.connect(self.mainwindow.mitmHandler.onCreateRuleForId)
        self.mainwindow.canLogView.createRuleForPayload.connect(self.mainwindow.mitmHandler.onCreateRuleForPayload)
        self.mainwindow.filterFramesByNewFramesAfterCheckbox.stateChanged.connect(self.onFilterAfterNFramesStateChanged)
        self.mainwindow.compactFilterCheckbox.stateChanged.connect(self.onFilterCompactChanged)
        self.mainwindow.highlightCheckbox.stateChanged.connect(self.onHighlightModeChanged)
        self.mainwindow.payloadFilterLineEdit.textEdited.connect(self.filterFrames)
        self.mainwindow.filterFramesByIdLineEdit.textEdited.connect(self.filterFrames)
        self.mainwindow.filterFramesAfterNSpinBox.valueChanged.connect(self.filterFrames)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.saveCanLogBtn.clicked.connect(self.onSaveFramesToFile)
        self.mainwindow.restoreCanLogBtn.clicked.connect(self.onReloadLogFromFile)
        self.data_timer.timeout.connect(self.retrieve_data)
        self.scroll_timer.timeout.connect(self.mainwindow.canLogView.scrollToBottom)
        self.mainwindow.canLogView.verticalScrollBar().sliderPressed.connect(self.disableAutoSlider)
        self.mainwindow.canLogView.verticalScrollBar().sliderMoved.connect(self.checkEnableAutoSlider)

    @Slot()
    def retrieve_data(self):
        if self.current_node_connection is None:
            return

        while True:
            try:
                ethMsg = self.current_node_connection.data_queue.get_nowait()
                self.cnt += 1

                if type(ethMsg) == EthernetMessage:
                    if ethMsg.msg_type != EthernetMessageType.DATA:
                        raise UnhandledEthernetMessageException(message_type=ethMsg.msg_type, action_type=ethMsg.action_type)
                    # parse EthernetMessage received from the canbadger
                    frame = self.can_parser.parseToCanFrame(ethMsg.data)
                else:
                    # data is tuple comping from socketCan, construct new CanFrame from it
                    (can_id, timestamp, data_len, data) = ethMsg
                    frame = self.can_parser.constructCanFrame(can_id, data_len, data, timestamp=timestamp)
                self.model.add_frame(QModelIndex(), frame)
            except Empty:
                break

        # call filters to have them updated
        if self.countSortProxy.filteringEnabled and self.countSortProxy.compactFilter:
            self.filterFrames()

    @Slot()
    def setup_gui(self):
        self.mainwindow.canLogView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mainwindow.canLogView.setSelectionMode(QAbstractItemView.SingleSelection)

    @Slot()
    def filterFrames(self):
        if self.model is None:
            return
        self.countSortProxy.invalidateFilter()

    @Slot()
    def onStartCanLogger(self):
        node = self.mainwindow.selectedNode

        # reset the ui model first
        self.renewModel()

        self.stopped = False

        if node is None or "connection" not in node:
            pass
        else:
            # node['connection'].newDataMessage.connect(self.onNewData)
            node['connection'].runCanlogger()
            self.mainwindow.startCanLoggerBtn.clicked.disconnect()
            self.mainwindow.startCanLoggerBtn.clicked.connect(self.onStopCanLogger)
            self.mainwindow.startCanLoggerBtn.setText("Stop")
            self.current_node_connection = node['connection']
            self.data_timer.start(100)  # check for data every 100ms

        self.scroll_timer.start(100)

    @Slot()
    def onStopCanLogger(self):
        self.data_timer.stop()
        self.scroll_timer.stop()
        self.cnt = 0
        self.stopped = True
        # gracefullyDisconnectSignal(self.mainwindow.selectedNode['connection'].newDataMessage)
        self.current_node_connection.stopCurrentAction()
        self.mainwindow.startCanLoggerBtn.clicked.disconnect()
        self.mainwindow.startCanLoggerBtn.clicked.connect(self.onStartCanLogger)
        self.mainwindow.startCanLoggerBtn.setText("Start")
        self.countSortProxy.filteringEnabled = True
        self.countSortProxy.setDynamicSortFilter(True)
        self.mainwindow.canLogView.resizeColumnToContents(2)
        self.mainwindow.canLogView.setSortingEnabled(True)
        self.filterFrames()


    @Slot(str)
    def onNewData(self, data):
        self.cnt += 1
        # print self.cnt
        frame = CanParser.parseSingleFrame(data)
        frame_entry = [self.cnt, frame['id'], frame['payload']]
        self.model.addFrame(frame_entry)

    @Slot(int)
    def onFilterAfterNFramesStateChanged(self, state):
        if self.countSortProxy is None:
            return

        if state == 2:
            self.countSortProxy.filterAfterNSamples = True
        else:
            self.countSortProxy.filterAfterNSamples = False
        self.countSortProxy.invalidate()

    @Slot(int)
    def onFilterCompactChanged(self, state):
        if self.countSortProxy is None:
            return

        if state == 2:
            self.countSortProxy.compactFilter = True
        else:
            self.countSortProxy.compactFilter = False
        self.countSortProxy.invalidate()

    @Slot(int)
    def onHighlightModeChanged(self, state):
        if self.countSortProxy is None:
            return

        if state == 2:
            self.countSortProxy.highlightMode = True
        else:
            self.countSortProxy.highlightMode = False
        self.countSortProxy.invalidate()

    # reset the view when when already displayed rows need to be filtered out
    @Slot(int)
    def resetView(self, row):
        if self.countSortProxy.filteringEnabled and self.countSortProxy.compactFilter:
            self.mainwindow.canLogView.reset()

    @Slot()
    def disableAutoSlider(self):
        self.scroll_timer.stop()

    @Slot()
    def checkEnableAutoSlider(self):
        # if the user moved the scollbar to the maximum offset, we enable autoslide

        value = self.mainwindow.canLogView.verticalScrollBar().value()
        maximum = self.mainwindow.canLogView.verticalScrollBar().maximum()
        # ass the maximum offset grows the bigger the difference between value and maximum when sliding the bar down
        # all the way can be, so we snap to auto_slide when reaching maximum - this inaccuracy
        inaccuracy = 1 + maximum // 100
        if value > maximum - inaccuracy:
            if not self.scroll_timer.isActive():
                self.scroll_timer.start(100)
        else:
            self.scroll_timer.stop()

    @Slot(object, dict)
    def onSelectedNodeChanged(self, previous, current):
        if current is not None:
            if previous is not None:
                if "canlogger" not in previous:
                    previous["canlogger"] = {}
                previous["canlogger"]["model"] = self.model
            if "canlogger" not in current:
                current["canlogger"] = {}
                current["canlogger"]["model"] = CanLoggerItemModel(self.mainwindow.canLogView)
            self.model = current["canlogger"]["model"]
            self.countSortProxy = CanLoggerSortModel(self.mainwindow)
            self.countSortProxy.setSourceModel(self.model)
            self.mainwindow.canLogView.setModel(self.countSortProxy)
            self.mainwindow.canLogView.setSortingEnabled(True)
            self.mainwindow.filterFramesByNewFramesAfterCheckbox.setCheckState(Qt.Unchecked)
            self.filterFrames()

    @Slot()
    def onSaveFramesToFile(self):
        filename = QFileDialog.getSaveFileName(self.mainwindow, 'Save CAN frames', '.', "*.csv")
        if len(filename) < 1:
            return

        # stringify all the frames
        frames = self.model.get_frame_list()

        filename = filename[0]
        # check for correct file ending
        if not filename.endswith('.csv'):
            if filename.rfind('.') == -1:
                filename += '.csv'
            else:
                filename = filename[:filename.rfind('.')] + '.csv'

        with open(filename, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(frames)

    @Slot()
    def onReloadLogFromFile(self):
        filename = QFileDialog.getOpenFileName(self.mainwindow, 'Load Log File', '.', "*.csv")
        if len(filename) < 1:
            return

        self.renewModel()

        with open(filename[0], newline='') as infile:
            reader = csv.reader(infile)
            for row in reader:
                frame = self.can_parser.constructCanFrame(int(row[4], 0), int(row[5]),
                                                          bytes([int(x, 0) for x in row[6:]]),
                                                          timestamp=int(row[0]), speed=int(row[3]),
                                                          interface=int(row[1].strip()[3:]))
                self.model.add_frame(QModelIndex(), frame)

    # get a new model to hold the data and reconnect view and sorting
    def renewModel(self):
        self.model = CanLoggerItemModel(self.mainwindow.canLogView)
        self.model.resetRow.connect(self.resetView)
        self.countSortProxy.filteringEnabled = True
        self.countSortProxy.setSourceModel(self.model)
        self.mainwindow.canLogView.setModel(self.countSortProxy)
        self.mainwindow.canLogView.setItemDelegate(FrameDelegate(model=self.model, proxy=self.countSortProxy))
        self.mainwindow.canLogView.setColumnWidth(2, 300)
        self.countSortProxy.sort(0)
