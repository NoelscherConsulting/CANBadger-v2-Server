#####################################################################################
# CanBadger Settings Handler                                                        #
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

from PySide2.QtCore import *

from helpers import *

class SettingsHandler(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(SettingsHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler

    def connect_signals(self):
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)

    @Slot(dict)
    def onSaveNodeSettings(self, node):
        text = self.mainwindow.nodeIdLineEdit.text()
        if text != node["id"] and len(text) > 0:
            # update settings
            gracefullyDisconnectSignal(node['connection'].ackReceived)
            gracefullyDisconnectSignal(node['connection'].nackReceived)
            node['connection'].ackReceived.connect(self.onSettingsAck)
            node['connection'].nackReceived.connect(self.onSettingsNack)
            node['connection'].updateSettings({ 'id': self.mainwindow.nodeIdLineEdit.text()})

    @Slot()
    def onSettingsAck(self):
        node = self.mainwindow.selectedNode
        gracefullyDisconnectSignal(node['connection'].ackReceived)
        gracefullyDisconnectSignal(node['connection'].nackReceived)
        self.mainwindow.onUpdateDebugLog("Settings saved!")

    @Slot()
    def onSettingsNack(self):
        node = self.mainwindow.selectedNode
        gracefullyDisconnectSignal(node['connection'].ackReceived)
        gracefullyDisconnectSignal(node['connection'].nackReceived)
        self.mainwindow.onUpdateDebugLog("Error saving settings!")

    @Slot(dict)
    def onSelectedNodeChanged(self, node):
        self.mainwindow.nodeIdLineEdit.setText("")
