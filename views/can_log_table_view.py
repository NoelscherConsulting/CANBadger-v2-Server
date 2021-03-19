#####################################################################################
# CanBadger Can Logger Table View                                                   #
# Copyright (c) 2021 Noelscher Consulting GmbH                                      #
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

from PySide2.QtCore import Signal, Slot
from PySide2.QtWidgets import QTableView, QMenu


class CanLogTableView(QTableView):
    sendToReplay = Signal(list)
    createRuleForId = Signal(list)
    createRuleForPayload = Signal(list)

    def __init__(self, parent):
        super(CanLogTableView, self).__init__(parent)
        self.verticalHeader().setVisible(False)

    def contextMenuEvent(self, event):
        # get current selection
        index = self.indexAt(event.pos())
        if index.row() >= 0 and index.column() >= 0:
            menu = QMenu()
            replayAction = menu.addAction("Send to Replay")
            replayAction.triggered.connect(self.onReplayActionTriggered)
            createRuleByIdAction = menu.addAction("Create Rule for ID")
            createRuleByIdAction.triggered.connect(self.onCreateRuleByIdActionTriggered)
            createRuleByPayloadAction = menu.addAction("Create Rule for Payload")
            createRuleByPayloadAction.triggered.connect(self.onCreateRuleByPayloadActionTriggered)

            action = menu.exec_(event.globalPos())

    @Slot()
    def onReplayActionTriggered(self):
        # frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().getFrame(self.currentIndex())
        self.sendToReplay.emit(frame)

    @Slot()
    def onCreateRuleByIdActionTriggered(self):
        # frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().getFrame(self.currentIndex())
        self.createRuleForId.emit(frame)

    @Slot()
    def onCreateRuleByPayloadActionTriggered(self):
        # frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().getFrame(self.currentIndex())
        self.createRuleForPayload.emit(frame)

