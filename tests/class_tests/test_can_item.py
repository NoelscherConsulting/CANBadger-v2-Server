#####################################################################################
# CanBadger CanItem Test                                                            #
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
sys.path.append('.')
from datatypes.can_frame import CanFrame
from datatypes.can_item import CanItem


def test_can_item():
    # make a valid frame
    cf = CanFrame.from_raw_canbadger_bytes(b'\x16\xaa\xaa\xaa\xaa\x00\x00\x02\x35\x40\x42\x0f\x00\x02\xcc\xdd') #make a valid frame

    # create can item and parent
    parent = CanItem()
    item = CanItem(parent=parent, frame=cf)
    parent.append_child(item)

    assert item.data(2) == str(b'\xcc\xdd')
    assert item.column_count() == 4
    assert parent.child_count() == 1
    assert parent.child(0) is item
