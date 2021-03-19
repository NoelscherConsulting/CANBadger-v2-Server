#####################################################################################
# CanBadger CanFrame Test                                                           #
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

import pytest
import sys
sys.path.append('.')
from datatypes.can_frame import CanFrame, CanFormat


def test_can_frame():
    # test valid CanFrame construction
    cf = CanFrame(1, CanFormat.Standard, 123422, 0x3AB, 50000, 8, b'\x01\x23\xf3\xa2\x52\x00\x00\xcc')
    assert cf.frame_format == CanFormat.Standard

    # test bad size for format
    with pytest.raises(AttributeError):
        cf = CanFrame(1, CanFormat.Standard, 123422, 0x3AB, 50000, 9, b'\xab\x01\x23\xf3\xa2\x52\x00\x00\xcc')

    # test invalid format
    with pytest.raises(AttributeError):
        cf = CanFrame(1, CanFormat.UNIDENTIFIED, 123422, 0x3AB, 50000, 8, b'\xab\x01\x23\xf3\xa2\x52\x00\x00')

    # test ids
    with pytest.raises(AttributeError):
        cf = CanFrame(1, CanFormat.Standard, 123422, 0x8CC, 50000, 8, b'\xab\x01\x23\xf3\xa2\x52\x00\x00')

    with pytest.raises(AttributeError):
        cf = CanFrame(1, CanFormat.CAN_FD, 123422, 0x2ABCDEF0, 50000, 8, b'\xab\x01\x23\xf3\xa2\x52\x00\x00')

    del cf
    cf = CanFrame(1, CanFormat.CAN_FD, 123422, 0x1ABCDEF0, 50000, 8, b'\xab\x01\x23\xf3\xa2\x52\x00\x00')
    assert cf.frame_format == CanFormat.CAN_FD
    assert cf.frame_payload == b'\xab\x01\x23\xf3\xa2\x52\x00\x00'

    # test parsing from binary
    cf = CanFrame.from_raw_canbadger_bytes(b'\x16\xaa\xaa\xaa\xaa\x00\x00\x02\x35\x40\x42\x0f\x00\x02\xcc\xdd')
    assert cf.frame_format == CanFormat.Standard
    assert cf.frame_payload == b'\xcc\xdd'
    assert cf.frame_id == 565
    assert cf.is_canfd() is False
    assert cf.get_column(2) == str(b'\xcc\xdd')

    with pytest.raises(AttributeError):
        cf = CanFrame.from_raw_canbadger_bytes(b'\x16\xaa\xaa\xaa\xaa\x35\x09\x00\x00\x00\x0f\x42\x40\x02\xcc\xdd')

    with pytest.raises(AttributeError):
        cf = CanFrame.from_raw_canbadger_bytes(b'\x16\xaa\xaa\xaa\xaa\x35\x02\x00\x00\x00\x1e\x85\x48\x02\xcc\xdd')

    with pytest.raises(AttributeError):
        cf = CanFrame.from_raw_canbadger_bytes(b'\x16\xaa\xaa\xaa\xaa\x35\x02\x00\x00\x00\x0f\x42\x40\x05\xcc\xdd')

    with pytest.raises(AttributeError):
        cf = CanFrame.from_raw_canbadger_bytes(b'\x35\xaa\xaa\xaa\xaa\x35\x02\x00\x00\x00\x0f\x42\x40\x02\xcc\xdd')
