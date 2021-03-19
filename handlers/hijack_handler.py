#####################################################################################
# CanBadger Hijack Handler                                                          #
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

from enum import IntEnum
from PySide2.QtCore import QObject, Slot

from canbadger_messages.security_hijack_message import SecurityHijackMessage
from canbadger_messages.security_hijack_response import SecurityHijackResponse
from canbadger_messages.ethernet_message import EthernetMessageType, EthernetMessage, ActionType
from handlers.node_handler import NodeHandler
from helpers import *


class HijackState(IntEnum):
    IDLE=0,
    BUSY=1,
    SUCCEEDED=2


class HijackHandler(QObject):
    def __init__(self, mainwindow, nodehandler: NodeHandler):
        super(HijackHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.selected_node = None
        self.state = HijackState.IDLE
        self.uds_handler = self.mainwindow.udsHandler

    def connect_signals(self):
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)

    def setup_ui(self):
        pass

    def setEnableUi(self, enable):
        self.mainwindow.securityHijackToolIdLineEdit.setEnabled(enable)
        self.mainwindow.securityHijackTargetIdLineEdit.setEnabled(enable)
        self.mainwindow.securityHijackSecurityLevelSpinBox.setEnabled(enable)
        self.mainwindow.securityHijackTargetSessionLevelSpinBox.setEnabled(enable)
        self.mainwindow.startSecurityHijackBtn.setEnabled(enable)


    @Slot(object,object)
    def onSelectedNodeChanged(self, prev_node, node):
        #self.selected_node = node
        if node is not None:
            self.setEnableUi(True)
            self.selected_node = node["connection"]
        else:
            self.setEnableUi(False)


    @Slot()
    def onStartHijack(self):
        local_id = int(self.mainwindow.securityHijackToolIdLineEdit.text(), 16)
        remote_id = int(self.mainwindow.securityHijackTargetIdLineEdit.text(), 16)
        level = int(self.mainwindow.securityHijackSecurityLevelSpinBox.value())
        sess_level = int(self.mainwindow.securityHijackTargetSessionLevelSpinBox.value())
        msg = SecurityHijackMessage(local_id, remote_id, level, sess_level)
        gracefullyDisconnectSignal(self.selected_node.newDataMessage)
        self.selected_node.newDataMessage.connect(self.onNewData)
        self.selected_node.sendEthernetMessage(msg)
        self.state = HijackState.BUSY


    @Slot(object)
    def onNewData(self, data):
        response = SecurityHijackResponse(EthernetMessage(EthernetMessageType.DATA, ActionType.NO_TYPE, len(data), data))
        if response.success:
            self.mainwindow.onUpdateDebugLog(f"Successfully performed SecurityHijack with session level {response.session_level}")
            self.state = HijackState.SUCCEEDED
            self.uds_handler.onSuccessfullyEstablishedSession()
        else:
            self.mainwindow.onUpdateDebugLog(
                f"Security Hijack failed!"
            )
            self.state = HijackState.IDLE



