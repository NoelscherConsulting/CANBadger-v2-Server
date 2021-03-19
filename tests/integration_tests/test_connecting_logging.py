#####################################################################################
# CanBadger Simulator Test                                                          #
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

from tools import CanbadgerSimulator
import pytest
from multiprocessing import Process
from main import MainWindow
from PySide2.QtCore import Qt


# process for running the canbadger simulator
class SimulatorProcess(Process):
    def __init__(self):
        super().__init__()
        self.cb_sim = None

    def run(self):
        self.cb_sim = CanbadgerSimulator()
        self.cb_sim.impostor()


# fixture starts the simulator before the following test, teminates the process afterwards
@pytest.fixture(autouse=True, scope='session')
def start_simulator():
    sim_proc = SimulatorProcess()
    sim_proc.start()

    yield

    sim_proc.terminate()


def test_connecting_disconnecting_from_gui(qtbot):

    mainWin = MainWindow()
    mainWin.show()
    qtbot.addWidget(mainWin)
    qtbot.wait(2000)
    if_select = mainWin.interfaceSelection
    qtbot.mouseClick(if_select, Qt.LeftButton)
    qtbot.wait(100)
    # check if we see the simulator running and can potentially connect to it
    assert(if_select.findText("cb_sim", Qt.MatchContains) != -1)

    num_connections = 10

    while num_connections > 0:
        if_select.setCurrentIndex(if_select.findText("cb_sim", Qt.MatchContains))
        qtbot.wait(500)
        assert(mainWin.nodeIdLineEdit.text() == "cb_sim")
        if_select.setCurrentIndex(if_select.findText("None", Qt.MatchContains))
        qtbot.wait(1000)
        assert (if_select.findText("cb_sim", Qt.MatchContains) != -1)

        num_connections -= 1



