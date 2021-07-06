#####################################################################################
# CanBadger Unhandled Ethernet Exception                                            #
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

# can be thrown by a handler that receives a bad type or action type that its not supposed to handle

class UnhandledEthernetMessageException(Exception):
    def __init__(self, message_type=None, action_type=None):
        if message_type is not None:
            if action_type is not None:
                self.message = f"Can't handle EthernetMessage of type {message_type.name} with action type {action_type.name}."
            else:
                self.message = f"Can't handle EthernetMessage of type {message_type.name}."
        else:
            if action_type is not None:
                self.message = f"Can't handle EthernetMessage with action type {action_type.name}."
            else:
                self.message = f"Can't handle unfit EthernetMessage due to type or action."
        super().__init__(self.message)
