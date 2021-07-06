#####################################################################################
# CanBadger MITM Handler                                                            #
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

from PySide2.QtWidgets import QAbstractItemView, QFileDialog, QToolTip
from bitstring import *
from copy import *

from libcanbadger import EthernetMessage, EthernetMessageType, ActionType
from models.mitm_table_model import *
from helpers import *
from canbadger import StatusBits
import os


class MITMHandler(QObject):

    rule_types = ["Swap Payload", "Swap Specific Bytes", "Add fixed Value to specific bytes",
                  "Substract fixed Value from specific bytes", "Multiply specific bytes", "Divide specific bytes",
                  "Increase specific bytes by fixed percentage", "Decrease specific bytes by fixed percentage",
                  "Drop Frame"]
    cond_types = ["Entire payload matches", "Specific bytes match",
                  "Specific bytes are greater", "Specific bytes are less"]

    def __init__(self, mainwindow, nodehandler):
        super(MITMHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.rulesEnabled = False
        self.model = MITMTableModel()
        self.currentRowModelIndex = None
        self.max2ndCondChars = 8
        self.rules_to_send = []
        self.rules_sent_counter = 0

    # SETUP FUNCTIONS

    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_ui)
        self.mainwindow.ruleTypeComboBox.currentIndexChanged.connect(self.onRuleTypeChanged)
        self.mainwindow.ruleCondComboBox.currentIndexChanged.connect(self.onCondChanged)
        self.mainwindow.addRuleBtn.clicked.connect(self.onAddRule)
        self.mainwindow.removeRuleBtn.clicked.connect(self.onRemoveRule)
        self.mainwindow.saveRulesBtn.clicked.connect(self.onSendRules)
        self.mainwindow.MITMFileButton.clicked.connect(self.onStartMitmFromFile)
        self.mainwindow.startMITMButton.clicked.connect(self.onStartTransmittingRules)
        self.mainwindow.conditionMessageIdLineEdit.textEdited.connect(self.onConditionMessageIdTextChanged)
        self.mainwindow.conditionValueLineEdit.textEdited.connect(self.onConditionValueTextChanged)
        self.mainwindow.conditionMaskLineEdit.textEdited.connect(self.onConditionMaskTextChanged)
        self.mainwindow.actionArgumentLineEdit.textEdited.connect(self.onActionArgumentTextChanged)
        self.mainwindow.actionMaskLineEdit.textEdited.connect(self.onActionMaskTextChanged)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)
        self.mainwindow.loadRulesFromFileBtn.clicked.connect(self.onLoadRules)
        self.mainwindow.saveRulesToFileBtn.clicked.connect(self.onSaveRulesToFile)

    @Slot()
    def setup_ui(self):
        self.mainwindow.rulesTableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.mainwindow.rulesTableView.setModel(self.model)
        self.selectionModel = self.mainwindow.rulesTableView.selectionModel()
        self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)
        # actions
        for rule_type in MITMHandler.rule_types:
            self.mainwindow.ruleTypeComboBox.addItem(rule_type)
        # conditions
        for cond_type in MITMHandler.cond_types:
            self.mainwindow.ruleCondComboBox.addItem(cond_type)

    # ON TAB CHANGE

    # check if working with rule files on the SD is available
    def check_conditions(self):
        if self.mainwindow.selectedNode is None or "settings" not in self.mainwindow.selectedNode.keys():
            self.enableRuleFilesToCB(False)
            return

        setting_bits = self.mainwindow.selectedNode["settings"][0]

        # get bit for sd usage
        sd_available = (setting_bits >> StatusBits.SD_ENABLED) % 2
        self.enableRuleFilesToCB(sd_available)

    # RULE GENERATING AND PERSISTENCE

    @Slot()
    def onAddRule(self):
        if self.mainwindow.selectedNode is None:
            return

        self.model.addRule(["Swap Payload", "Specific bytes match", "", "",
                            "00000000", "", "00000000"])
        self.currentRowModelIndex = self.selectionModel.currentIndex()
        if self.selectionModel.hasSelection():
            self.setRuleEditingEnabled(True)
        else:
            self.setRuleEditingEnabled(False)
        self.mainwindow.conditionMaskLineEdit.setInputMask('B'*8)
        self.mainwindow.actionMaskLineEdit.setInputMask('B'*8)
        self.onCurrentRowChanged(self.currentRowModelIndex, QModelIndex())

    @Slot()
    def onRemoveRule(self):
        self.model.removeRule(self.currentRowModelIndex)
        self.currentRowModelIndex = None
        if self.selectionModel.hasSelection():
            self.currentRowModelIndex = self.selectionModel.currentIndex()
            self.setRuleEditingEnabled(True)
        else:
            self.setRuleEditingEnabled(False)

        if self.model.isEmpty():
            self.setRuleEditingEnabled(False)

    @Slot()
    def onLoadRules(self):
        filename = QFileDialog.getOpenFileName(self.mainwindow, 'Open rules file', '.', "Text files (*.txt)",
                                               "Text files (*.txt)")
        if filename is None or filename[0] == '':
            return

        with open(filename[0], 'r') as infile:
            rules = infile.readlines()
            if len(rules) < 1:
                return

        # remove current model entries
        self.model.clear()

        # parse each rule from txt format into model
        for rule in rules:
            values = rule.split(',')
            if len(values) != 19:
                continue  # invalid rule entry

            # extract payloads and id directly
            target_id = values[1]
            condition_payload = ''.join(values[2:10])
            argument_payload = ''.join(values[11:])

            # values[0] is 4 chars representing 2byte, first byte for the condition mask, 2nd byte for condition type
            condition = self.cond_types[int(values[0][2:], 16)]
            # get the binary representation of the mask as string, mask is saved flipped
            condition_mask = format(int(values[0][:2], 16), '08b')[::-1]

            # values[10] is representing 2byte, 1st byte for argument mask, 2nd byte for rule type
            rule_type = self.rule_types[int(values[10][2:], 16)]
            # get the binary representation of the mask as string, mask is saved flipped
            argument_mask = format(int(values[10][:2], 16), '08b')[::-1]

            self.model.addRule([rule_type, condition, target_id, condition_payload, condition_mask, argument_payload,
                                argument_mask])

    @Slot()
    def onSaveRulesToFile(self):
        filename = QFileDialog.getSaveFileName(self.mainwindow, 'Save rules file', '.', "Text files (*.txt)",
                                               "Text files (*.txt)")
        if filename is None or filename[0] == '':
            return

        formatted_rules = self.getFormattedRules()

        if len(formatted_rules) > 0:
            with open(filename[0], 'w') as outfile:
                outfile.writelines(formatted_rules)

    @Slot()
    def onSendRules(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return

        # get the rules in canbadger usable .txt format
        formatted_rules = self.getFormattedRules()
        if len(formatted_rules) < 1:
            return

        # check for entered filename, and check length, filetype etc.
        filename = self.getRuleFileName()

        temp_filepath = 'tmp_rules.txt'
        if len(formatted_rules) > 0:
            with open(temp_filepath, 'w+') as file:
                file.writelines(formatted_rules)

        # call the sd handler to upload the rule file
        self.mainwindow.sdHandler.upload_result.connect(self.displayRuleSaveResult)
        self.mainwindow.sdHandler.onUploadFile(filename, local_filename=temp_filepath, sd_path='/MITM')
        os.remove(temp_filepath)

    # get the content of the filename line edit, but check for .txt ending, non emptyness and max length
    def getRuleFileName(self):
        filename = self.mainwindow.ruleNameLineEdit.text()
        if filename == "":  # if no name is given, use default "rules.txt"
            self.mainwindow.ruleNameLineEdit.setText("rules.txt")
            filename = self.mainwindow.ruleNameLineEdit.text()
        if filename[-4:] != ".txt":  # make sure we send a txt to the canbadger
            dot_index = filename.find(".")
            if dot_index == -1:
                filename += ".txt"
            else:
                filename = filename[:dot_index] + ".txt"
        if len(filename) > 16:  # need to trim filename to max 16 chars
            filename = filename[:14] + filename[-4:]
        self.mainwindow.ruleNameLineEdit.setText(filename)
        return filename

    def getFormattedRules(self):
        rules = self.model.getRules()
        formatted_rules = []
        for rule in rules:
            # crazily format the rule string
            rule_str = str()
            condition_type = str(self.cond_types.index(rule[1]))
            condition_mask = BitArray(8)
            condition_mask.set(True, [i for i, ltr in enumerate(str(rule[4])) if ltr == '1'])
            condition_mask.reverse()
            rule_str += str(condition_mask)[2:] + '0' + str(condition_type) + ','
            # rule_str += str(condition_mask)[2:] + str(condition_type) + ','
            rule_str += str(rule[2]) + ',' if rule[2] != "" else "0,"
            cond_pl_string = ''
            for i in range(0, 16, 2):
                if i + 1 > len(rule[3]):
                    cond_pl_string += '00,'  # pad with 0s
                else:
                    cond_pl_string += str(rule[3][i]) + str(rule[3][i + 1]) + ','
            rule_str += cond_pl_string
            action_mask = BitArray(8)
            action_mask.set(True, [i for i, ltr in enumerate(str(rule[6])) if ltr == '1'])
            action_mask.reverse()
            rule_str += str(action_mask)[2:] + '0' + str(self.rule_types.index(rule[0])) + ','
            action_pl_string = ''
            for i in range(0, 16, 2):
                if i + 1 > len(rule[5]):
                    action_pl_string += '00,'  # pad with 0s
                else:
                    action_pl_string += str(rule[5][i]) + str(rule[5][i + 1]) + ','
            rule_str += action_pl_string[:-1]
            formatted_rules.append(rule_str + '\n')
        return formatted_rules

    # MITM START / STOP

    # start transmission of rules directly into xram
    @Slot()
    def onStartTransmittingRules(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return

        # switch button functionality
        self.mainwindow.MITMFileButton.setText("Stop")
        gracefullyDisconnectSignal(self.mainwindow.MITMFileButton.clicked)
        self.mainwindow.MITMFileButton.clicked.connect(self.onStopMitm)
        self.mainwindow.startMITMButton.setText("Stop")
        gracefullyDisconnectSignal(self.mainwindow.startMITMButton.clicked)
        self.mainwindow.startMITMButton.clicked.connect(self.onStopMitm)

        # set feedback handlers
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onRuleReceiveACK)
        connection.nackReceived.connect(self.onRuleReceiveError)

        # send command
        connection.sendEthernetMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.RECEIVE_RULES, 0, b''))

    def sendNextRule(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return
        connection = node['connection']

        # check that the parsed rules are available
        if not self.rules_to_send:
            self.rules_to_send = self.getFormattedRules()

        # select rule by counter as payload
        payload = self.rules_to_send[self.rules_sent_counter].encode('ascii')[:-1] + '\0'.encode('ascii')
        self.rules_sent_counter += 1

        # if all rules are sent, formatted rules can be discarded
        if self.rules_sent_counter >= len(self.rules_to_send):
            self.rules_sent_counter = 0
            self.rules_to_send = []

            # reconnect ack callback
            gracefullyDisconnectSignal(connection.ackReceived)
            connection.ackReceived.connect(self.onAllRulesTransmitted)

        # send rule previously selected
        connection.sendEthernetMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.ADD_RULE, len(payload), payload))

    # start MITM mode from rulefile
    @Slot()
    def onStartMitmFromFile(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return

        # check for selected rulefile
        filename = self.getRuleFileName()
        msg_data = filename.encode('ascii') + b'\0'

        # switch button functionality
        self.mainwindow.MITMFileButton.setText("Stop")
        gracefullyDisconnectSignal(self.mainwindow.MITMFileButton.clicked)
        self.mainwindow.MITMFileButton.clicked.connect(self.onStopMitm)
        self.mainwindow.startMITMButton.setText("Stop")
        gracefullyDisconnectSignal(self.mainwindow.startMITMButton.clicked)
        self.mainwindow.startMITMButton.clicked.connect(self.onStopMitm)

        # set feedback handlers
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onMITMFileAck)
        connection.nackReceived.connect(self.onMITMFileError)

        # send command
        connection.sendEthernetMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.ENABLE_MITM_MODE, len(msg_data),
                                               msg_data))

    # stop MITM execution on the canbadger
    @Slot()
    def onStopMitm(self):
        node = self.mainwindow.selectedNode
        if node is not None:
            # send command
            connection = node['connection']
            connection.sendEthernetMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.STOP_CURRENT_ACTION, 0, b''))

        # switch button functionality

        # ensure upper button is reset
        self.mainwindow.MITMFileButton.setText("MITM from File")
        gracefullyDisconnectSignal(self.mainwindow.MITMFileButton.clicked)
        self.mainwindow.MITMFileButton.clicked.connect(self.onStartMitmFromFile)

        # ensure lower button is reset
        self.mainwindow.startMITMButton.setText("Start MITM")
        gracefullyDisconnectSignal(self.mainwindow.startMITMButton.clicked)
        self.mainwindow.startMITMButton.clicked.connect(self.onStartTransmittingRules)

    # mitm start from rulefile was successful
    @Slot()
    def onMITMFileAck(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        buttonFeedback(True, self.mainwindow.MITMFileButton)

    # mitm start from rulefile failed
    @Slot()
    def onMITMFileError(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        buttonFeedback(False, self.mainwindow.MITMFileButton)

    # canbadger failed persisting mitm rule, abort
    @Slot()
    def onRuleReceiveError(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        buttonFeedback(False, self.mainwindow.startMITMButton)
        self.onStopMitm()

    # canbadger is ready to receive next rule
    @Slot()
    def onRuleReceiveACK(self):
        self.sendNextRule()

    # all rules have been received by the canbadger
    @Slot()
    def onAllRulesTransmitted(self):
        node = self.mainwindow.selectedNode
        if node is None:
            return
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)

        buttonFeedback(True, self.mainwindow.startMITMButton)
        connection.sendEthernetMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.MITM, 0, b''))

    # GUI CALLBACKS

    @Slot(QModelIndex, QModelIndex)
    def onCurrentRowChanged(self, current, prev):
        if not current is None:
            self.currentRowModelIndex = current
            self.setRuleEditingEnabled(True)
            rule = self.model.getRule(self.currentRowModelIndex)
            self.mainwindow.ruleTypeComboBox.setCurrentIndex(MITMHandler.rule_types.index(rule[0]))
            self.mainwindow.ruleCondComboBox.setCurrentIndex(MITMHandler.cond_types.index(rule[1]))
            self.mainwindow.conditionMessageIdLineEdit.setText(rule[2])
            if type(rule[3]) == QByteArray:
                self.mainwindow.conditionValueLineEdit.setText(str(rule[3]))
            else:
                self.mainwindow.conditionValueLineEdit.setText(rule[3])
            self.mainwindow.conditionMaskLineEdit.setText(rule[4])
            self.mainwindow.actionArgumentLineEdit.setText(rule[5])
            self.mainwindow.actionMaskLineEdit.setText(rule[6])
        else:
            self.setRuleEditingEnabled(False)

    # enable or disable the upload for rulefiles and the MITM start with rulefile (for when no SD is available)
    @Slot(bool)
    def enableRuleFilesToCB(self, enable):

        if not enable:
            self.mainwindow.ruleNameLineEdit.setPlaceholderText("SD not available")
            self.mainwindow.saveRulesBtn.setEnabled(False)
            self.mainwindow.MITMFileButton.setEnabled(False)
        else:
            self.mainwindow.ruleNameLineEdit.setPlaceholderText("Desired Filename (e.g. rules.txt)")
            self.mainwindow.saveRulesBtn.setEnabled(True)
            self.mainwindow.MITMFileButton.setEnabled(True)

    @Slot(int)
    def onRuleTypeChanged(self, index):
        if self.currentRowModelIndex is not None:
            self.model.updateRule(self.currentRowModelIndex, {'Rule Type': MITMHandler.rule_types[index]})

    @Slot(int)
    def onCondChanged(self, index):
        if self.currentRowModelIndex is not None:
            self.model.updateRule(self.currentRowModelIndex, {'Rule Condition': MITMHandler.cond_types[index]})

    @Slot(str)
    def onConditionMessageIdTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex, {'Target ID': newText})

    @Slot(str)
    def onConditionValueTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex,
                              {'Cond Value': newText})

    @Slot(str)
    def onConditionMaskTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex,
                              {'Cond Mask': newText})

    @Slot(str)
    def onActionArgumentTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex, {'Argument': newText})

    @Slot(str)
    def onActionMaskTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex, {'Action Mask': newText})

    def setRuleEditingEnabled(self, value):
        self.mainwindow.removeRuleBtn.setEnabled(value)
        self.mainwindow.ruleTypeComboBox.setEnabled(value)
        self.mainwindow.ruleCondComboBox.setEnabled(value)
        self.mainwindow.conditionValueLineEdit.setEnabled(value)
        self.mainwindow.conditionMaskLineEdit.setEnabled(value)
        self.mainwindow.conditionMessageIdLineEdit.setEnabled(value)
        self.mainwindow.actionArgumentLineEdit.setEnabled(value)
        self.mainwindow.actionMaskLineEdit.setEnabled(value)

    ##
    # these two methods are used to pass frames between modules

    @Slot(list)
    def onCreateRuleForId(self, frame):
        if self.mainwindow.selectedNode is None:
            return
        self.onAddRule()
        self.currentRowModelIndex = self.selectionModel.currentIndex()
        self.model.updateRule(self.currentRowModelIndex, {'Rule Condition': MITMHandler.cond_types[1]})
        self.model.updateRule(self.currentRowModelIndex, {'Target ID': deepcopy(frame[1])})
        self.onCurrentRowChanged(self.currentRowModelIndex, 0)
        self.mainwindow.tabWidget_2.tabBar().setTabTextColor(5, Qt.yellow)

    @Slot(list)
    def onCreateRuleForPayload(self, frame):
        if self.mainwindow.selectedNode is None:
            return
        self.onAddRule()
        self.currentRowModelIndex = self.selectionModel.currentIndex()
        self.model.updateRule(self.currentRowModelIndex, {'Cond Value': deepcopy(frame[2])})
        self.model.updateRule(self.currentRowModelIndex, {'Cond Mask': "11111111"})
        self.onCurrentRowChanged(self.currentRowModelIndex, 0)
        self.mainwindow.tabWidget_2.tabBar().setTabTextColor(5, Qt.yellow)

    @Slot(int)
    def onTabChanged(self, index):
        if index == 5:
            self.mainwindow.tabWidget_2.tabBar().setTabTextColor(5, Qt.black)

    @Slot(object, dict)
    def onSelectedNodeChanged(self, previous, current):
        if current is not None:
            if previous is not None:
                if "mitm" not in previous:
                    previous["mitm"] = {}
                previous["mitm"]["model"] = self.model
            if "mitm" not in current:
                current["mitm"] = {}
                current["mitm"]["model"] = MITMTableModel()
            self.model = current["mitm"]["model"]
            self.mainwindow.rulesTableView.setModel(self.model)
            self.selectionModel = self.mainwindow.rulesTableView.selectionModel()
            gracefullyDisconnectSignal(self.selectionModel.currentRowChanged)
            self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)

        self.setRuleEditingEnabled(False)

    # VISUAL FEEDBACK HELPERS

    @Slot(bool)
    def displayRuleSaveResult(self, result):
        gracefullyDisconnectSignal(self.mainwindow.sdHandler.upload_result)

        buttonFeedback(result, self.mainwindow.saveRulesBtn)







