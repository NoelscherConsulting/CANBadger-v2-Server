#####################################################################################
# CanBadger GUI                                                                     #
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

import sys
import platform
from PySide2.QtWidgets import QMainWindow

from handlers.can_logger import *
from handlers.mitm_handler import *
from handlers.sd_handler import *
from handlers.replay_handler import *
from handlers.settings_handler import *
from handlers.node_handler import *
from helpers import *
from window_specification import Ui_MainWindow
from canbadger import StatusBits
from multiprocessing import freeze_support


def can_filter(if_name):
    match = re.search("[cC][aA][nN]", if_name)
    return match is not None


class MainWindow(QMainWindow, Ui_MainWindow):
    connectToNode = Signal(dict)
    disconnectNode = Signal(dict)
    nodeIDChange = Signal(str, str)
    selectedNodeChanged = Signal(object, dict)
    socketCanDiscovered = Signal(str)
    exiting = Signal()
    mainInitDone = Signal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.resetBtn.setEnabled(False)

        # set up node handler
        self.nodeHandlerThread = EventProcessingThread()
        self.nodeHandler = NodeHandler(self)
        self.nodeHandler.moveToThread(self.nodeHandlerThread)
        self.nodeHandlerThread.started.connect(self.nodeHandler.onRun)
        self.nodeHandlerThread.start()

        # set up action classes
        self.canLogger = CanLogger(self, self.nodeHandler)
        # self.udsHandler = UDSHandler(self, self.nodeHandler)
        # self.tpHandler = TPHandler(self, self.nodeHandler)
        # self.hijackHandler = HijackHandler(self, self.nodeHandler)
        self.mitmHandler = MITMHandler(self, self.nodeHandler)
        self.sdHandler = SdHandler(self, self.nodeHandler)
        self.replayHandler = ReplayHandler(self, self.nodeHandler)
        self.settingsHandler = SettingsHandler(self, self.nodeHandler)

        # timer to check for socket can interfaces
        self.can_check_timer = QTimer(self)

        self.connectSignals()
        self.show()

        self.selectedNode = None
        self.selectionFlag = False  # signals that a disconnect was caused by a different selection

        if platform.system() == "Linux":  # socket can only available on linux
            self.can_check_timer.start(500)
        self.mainInitDone.emit()

    def connectSignals(self):

        # connect input signals
        self.interfaceSelection.currentIndexChanged.connect(self.onNodeItemClicked)
        self.tabWidget.tabBar().currentChanged.connect(self.onTabChanged)
        self.saveNodeSettingsBtn.clicked.connect(self.onSaveSettingsOnCB)
        self.eepromBtn.clicked.connect(self.onSaveSettingsOnEEPROM)
        self.resetBtn.clicked.connect(self.onResetButton)

        # connect 'command' signals
        self.connectToNode.connect(self.nodeHandler.onConnectToNode)
        self.disconnectNode.connect(self.nodeHandler.onDisconnectNode)
        self.nodeIDChange.connect(self.nodeHandler.onIDChange)
        self.socketCanDiscovered.connect(self.nodeHandler.onSocketCanDiscovered)

        # connect main functions to node handler signals
        self.nodeHandler.newNodeDiscovered.connect(self.onNewNodeDiscovered)
        self.nodeHandler.nodeDisappeared.connect(self.onNodeDisappeared)
        self.nodeHandler.nodeDisconnected.connect(self.onNodeDisconnected)
        self.nodeHandler.nodeConnected.connect(self.onNodeConnected)
        self.nodeHandler.cleanupDone.connect(self.onCloseDone)
        self.nodeHandler.nodeAliveMessage.connect(self.onUpdateNodeAlive)

        # exit related signals
        self.actionExit.triggered.connect(self.onExit)
        self.exiting.connect(self.nodeHandler.onExiting)

        # connect all the handlers to the signals
        self.canLogger.connect_signals()
        # self.udsHandler.connect_signals()
        # self.tpHandler.connect_signals()
        # self.hijackHandler.connect_signals()
        self.mitmHandler.connect_signals()
        self.sdHandler.connect_signals()
        self.replayHandler.connect_signals()
        self.settingsHandler.connect_signals()

        # connect timer to check for socket can interfaces
        self.can_check_timer.timeout.connect(self.check_socket_can)

    @Slot()
    def check_socket_can(self):
        interfaces = list()
        for line in open('/proc/net/dev', 'r'):
            if ':' in line:
                interfaces.append(line.split(':')[0].strip())
        interfaces = list(filter(can_filter, interfaces))
        for vcan in interfaces:
            self.socketCanDiscovered.emit(vcan)


    @Slot(int)
    def onNodeItemClicked(self, index):
        node = self.interfaceSelection.itemData(index)

        # when disconnecting a node, the interfaceSelections currentIndexChanged Signal will trigger,
        # again calling this function.
        # so if the newly selected node is the currently selected node, we skip disconnecting and connecting
        if node is not None and self.selectedNode is not None and (node['id'] == self.selectedNode['id']):
            return

        print(' ')
        if node is None:
            print("--- None selected!!")
        else:
            print(f"--- {node['id']} selected!")

        prev_node = self.selectedNode
        self.selectedNode = node

        # switch sd_handler model to a new one on new connection
        self.sdHandler.fileModel = SD_FS_Model(self.sdHandler.fileBrowser)
        self.sdHandler.fileBrowser.setModel(self.sdHandler.fileModel)
        self.sdHandler.busy = False

        # we want to disconnect from the old node
        if prev_node is not None:
            if self.selectedNode is not None:
                self.selectionFlag = True  # set selectionFlag on connection change
            self.disconnectNode.emit(prev_node)

        # connect to the newly selected interface
        if node is not None:
            self.connectToNode.emit(node)

    @Slot(dict)
    def onNewNodeDiscovered(self, node):
        if node["version"] != "socket_can":
            self.interfaceSelection.addItem(node["id"] + ':' + node["ip"], node)
        else:
            self.interfaceSelection.addItem(node["id"] + ':' + "SocketCan", node)

    @Slot(dict)
    def onNodeDisappeared(self, node):
        # go through all items, find the matching one and remove it
        if node["version"] != "socket_can":
            row = self.interfaceSelection.findText("%s:%s" % (node["id"], node["ip"]), Qt.MatchContains)
        else:
            row = self.interfaceSelection.findText("%s:%s" % (node["id"], "SocketCan"), Qt.MatchContains)
        self.interfaceSelection.removeItem(row)

    @Slot(dict)
    def onNodeDisconnected(self, node):
        # disconnect settings displays from change functions
        gracefullyDisconnectSignal(self.enableCAN1Checkbox.stateChanged)
        gracefullyDisconnectSignal(self.enableCAN2Checkbox.stateChanged)
        gracefullyDisconnectSignal(self.enableBRIDGE1Checkbox.stateChanged)
        gracefullyDisconnectSignal(self.enableBRIDGE2Checkbox.stateChanged)
        gracefullyDisconnectSignal(self.CAN1SpeedSelection.activated)
        gracefullyDisconnectSignal(self.CAN2SpeedSelection.activated)

        # reset all displays
        if node["version"] != "socket_can":
            row = self.interfaceSelection.findText("%s:%s" % (node["id"], node["ip"]), Qt.MatchContains)
        else:
            row = self.interfaceSelection.findText("%s:%s" % (node["id"], "SocketCan"), Qt.MatchContains)
        self.resetBtn.setEnabled(False)

        # if we dont connect to a new node and only disconnected, change to None
        if not self.selectionFlag and self.interfaceSelection.currentText() != "None":
            self.interfaceSelection.setCurrentIndex(self.interfaceSelection.findText("None", Qt.MatchExactly))
        self.selectionFlag = False

        # reset settings displays
        self.interfaceSelection.removeItem(row)
        self.nodeIdLineEdit.setText("")
        self.enableBRIDGE1Checkbox.setChecked(False)
        self.enableBRIDGE2Checkbox.setChecked(False)
        self.enableCAN1Checkbox.setChecked(False)
        self.enableCAN2Checkbox.setChecked(False)
        self.CAN1SpeedSelection.insertItem(0, "")
        self.CAN2SpeedSelection.insertItem(0, "")
        self.CAN1SpeedSelection.setCurrentIndex(self.CAN1SpeedSelection.findText("", Qt.MatchExactly))
        self.CAN2SpeedSelection.setCurrentIndex(self.CAN2SpeedSelection.findText("", Qt.MatchExactly))
        self.startCanLoggerBtn.setText("Not Connected")
        self.canbadgerSettingsGrpBox.show()
        self.canSettingsGrpBox.show()
        self.saveNodeSettingsBtn.show()

    @Slot(dict)
    def onNodeConnected(self, node):
        self.nodeIdLineEdit.setText(node["id"])
        selected = self.interfaceSelection.currentIndex()
        self.interfaceSelection.setItemText(selected, self.interfaceSelection.itemText(selected) + '  -  connected')
        self.startCanLoggerBtn.setText("Start Logging")
        self.startCanLoggerBtn.clicked.disconnect()
        self.startCanLoggerBtn.clicked.connect(self.canLogger.onStartCanLogger)
        self.resetBtn.setEnabled(True)

        # hide settings elements when using socketCan
        if node["version"] == "socket_can":
            self.canSettingsGrpBox.hide()
            self.canbadgerSettingsGrpBox.hide()
            self.saveNodeSettingsBtn.hide()

    @Slot(str)
    def onUpdateDebugLog(self, msg):
        self.debugLogPlainTextEdit.appendPlainText(msg)
        self.tabWidget.tabBar().setTabTextColor(0, Qt.yellow)
        self.statusbar.showMessage(msg)

    # used to trigger different functions that need to run on change to specific tabs
    @Slot(int)
    def onTabChanged(self, index):

        if index == 4:  # SD TAB
            # check for SD contents on tab change
            self.sdHandler.onUpdateSd(caller="tab")

        if index == 3:  # MITM TAB
            # check SD availability
            self.mitmHandler.check_conditions()

    @Slot(dict)
    def onUpdateNodeAlive(self, node):
        # previously updated last seen TODO remove?
        pass

    @Slot(object)
    def onSettingsReceived(self, msg_data):
        # extract id
        id_length = msg_data[0]
        if id_length < 0 or id_length > 18:
            return  # invalid length
        canbadger_id = msg_data[1:id_length+1].decode('ascii')
        self.selectedNode["id"] = canbadger_id

        # extract ip string
        ip_length = msg_data[id_length + 1]
        speeds_start = id_length + ip_length + 2
        settings_ip_string = msg_data[id_length + 2:speeds_start]
        self.selectedNode["settings_ip_string"] = settings_ip_string

        if len(msg_data[speeds_start:]) != 6*4:
            return  # rest of the message is wrong length

        # display the recieved settings to the user
        self.nodeIdLineEdit.setText(self.selectedNode["id"])
        settings, spi_speed, can1speed, can2speed, kl1spd, kl2spd = struct.unpack('<IIIIII', msg_data[speeds_start:])
        self.CAN1SpeedSelection.setCurrentIndex(self.CAN1SpeedSelection.findText("%d" % can1speed, Qt.MatchContains))
        self.CAN2SpeedSelection.setCurrentIndex(self.CAN2SpeedSelection.findText("%d" % can2speed, Qt.MatchContains))
        self.CAN1SpeedSelection.removeItem(self.CAN1SpeedSelection.findText("", Qt.MatchExactly))
        self.CAN2SpeedSelection.removeItem(self.CAN2SpeedSelection.findText("", Qt.MatchExactly))

        self.enableCAN1Checkbox.setChecked((settings >> StatusBits.CAN1_LOGGING) % 2)
        self.enableCAN2Checkbox.setChecked((settings >> StatusBits.CAN2_LOGGING) % 2)
        self.enableBRIDGE1Checkbox.setChecked((settings >> StatusBits.CAN1_TO_CAN2_BRIDGE) % 2)
        self.enableBRIDGE2Checkbox.setChecked((settings >> StatusBits.CAN2_TO_CAN1_BRIDGE) % 2)

        # keep the settings for the current node
        self.selectedNode["settings"] = (settings, spi_speed, can1speed, can2speed, kl1spd, kl2spd)

        # connect the inputs so setting changes can be handled
        self.enableCAN1Checkbox.stateChanged.connect(self.onSettingsChange)
        self.enableCAN2Checkbox.stateChanged.connect(self.onSettingsChange)
        self.enableBRIDGE1Checkbox.stateChanged.connect(self.onSettingsChange)
        self.enableBRIDGE2Checkbox.stateChanged.connect(self.onSettingsChange)
        self.CAN1SpeedSelection.activated.connect(self.onSettingsChange)
        self.CAN2SpeedSelection.activated.connect(self.onSettingsChange)

    @Slot()
    def onSaveSettingsOnCB(self):
        if self.selectedNode is None or "settings" not in self.selectedNode.keys() or\
                self.selectedNode["settings"] is None:
            return  # not connected

        # get the current input in the id field, update local settings (max cb id is 18 chars)
        if len(self.nodeIdLineEdit.text()) <= 18 and self.selectedNode["id"] != self.nodeIdLineEdit.text():
            self.nodeIDChange.emit(self.selectedNode["id"], self.nodeIdLineEdit.text())
            row = self.interfaceSelection.findText("%s:%s" %
                                                   (self.selectedNode["id"], self.selectedNode["ip"]), Qt.MatchContains)
            self.selectedNode["id"] = self.nodeIdLineEdit.text()
            self.interfaceSelection.setItemText(row, self.selectedNode["id"] + ':'
                                                + self.selectedNode["ip"] + '  -  connected')
        else:
            self.nodeIdLineEdit.setText(self.selectedNode["id"])

        # send settings to canbadger
        payload = len(self.selectedNode["id"]).to_bytes(1, 'big') + bytes(self.selectedNode["id"], 'ascii')
        payload += len(self.selectedNode["settings_ip_string"]).to_bytes(1, 'big') + self.selectedNode["settings_ip_string"]
        payload += struct.pack('<%dI' % len(self.selectedNode["settings"]), *self.selectedNode["settings"])
        eth_msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.SETTINGS, len(payload), payload)

        # send settings to canbadger
        self.selectedNode["connection"].sendEthernetMessage(eth_msg)

    @Slot()
    def onSaveSettingsOnEEPROM(self):
        if self.selectedNode is None or "settings" not in self.selectedNode.keys() or\
                self.selectedNode["settings"] is None:
            return  # not connected
        self.onSaveSettingsOnCB()
        eth_msg = EthernetMessage(EthernetMessageType.ACTION, ActionType.EEPROM_WRITE, 0, b'')
        self.selectedNode["connection"].sendEthernetMessage(eth_msg)

    @Slot()
    def onSettingsChange(self):
        if "settings" not in self.selectedNode.keys() or self.selectedNode["settings"] is None:
            return  # cant change settings if there are no settings

        caller = QObject.sender(self)

        # handle checkbox changes
        if caller.objectName() == "enableCAN1Checkbox":
            self.selectedNode["settings"] = (self.selectedNode["settings"][0] ^ (1 << StatusBits.CAN1_LOGGING), ) \
                                            + self.selectedNode["settings"][1:]
        elif caller.objectName() == "enableCAN2Checkbox":
            self.selectedNode["settings"] = (self.selectedNode["settings"][0] ^ (1 << StatusBits.CAN2_LOGGING), ) \
                                            + self.selectedNode["settings"][1:]
        elif caller.objectName() == "enableBRIDGE1Checkbox":
            self.selectedNode["settings"] = (self.selectedNode["settings"][0]
                                             ^ (1 << StatusBits.CAN1_TO_CAN2_BRIDGE), ) \
                                            + self.selectedNode["settings"][1:]
        elif caller.objectName() == "enableBRIDGE2Checkbox":
            self.selectedNode["settings"] = (self.selectedNode["settings"][0]
                                             ^ (1 << StatusBits.CAN2_TO_CAN1_BRIDGE), ) \
                                            + self.selectedNode["settings"][1:]

        # handle speed selection changes
        if caller.objectName() == "CAN1SpeedSelection":
            self.selectedNode["settings"] = self.selectedNode["settings"][0:2] + \
                                            (int(self.CAN1SpeedSelection.currentText()), ) + \
                                            self.selectedNode["settings"][3:]
        elif caller.objectName() == "CAN2SpeedSelection":
            self.selectedNode["settings"] = self.selectedNode["settings"][0:3] + \
                                            (int(self.CAN2SpeedSelection.currentText()), ) + \
                                            self.selectedNode["settings"][4:]

    @Slot()
    def onResetButton(self):
        # send reset command to the canbadger and disconnect from it
        if self.selectedNode is None:
            return
        connection = self.selectedNode['connection']
        if connection is None:
            return

        # disconnect from CB on GUI side
        self.disconnectNode.emit(self.selectedNode)


    @Slot()
    def onExit(self):
        # stop all ongoing things
        self.exiting.emit()

    def closeEvent(self, event):
        self.exiting.emit()
        event.ignore()

    @Slot()
    def onCloseDone(self):
        sys.exit(0)

    # additional key handling for some comfort functions
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete:
            # check if we are in the SD tab
            tab_text = self.tabWidget.tabText(self.tabWidget.currentIndex())
            if tab_text == "Manage SD Card":
                self.sdHandler.onDeleteFile()



if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    ret = app.exec_()
    sys.exit(ret)
