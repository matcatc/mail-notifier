#!/usr/bin/python3
'''
Simple script which notifies user when a new mail comes in.

Works by keeping track of unread mail and notifying user when it increases.

TODO: program arguments
    config file?

TODO: handle import errors for notify2?
    Continue running and use another method vs quiting?

TODO: logging?

@license
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author Matthew Todd
@date Dec 16, 2012
'''

# standard modules
import subprocess
import time

# 3rd party modules
import notify2


# constants
SLEEP_TIME = 10

# msg claws-mail output when its not running. Unlikely to change, but could.
CLAWS_MAIL_NOT_RUNNING = '0 Claws Mail not running.'


class MailInfo:
    '''
    Probably overkill, but made it cleaner IMO. Also allows for future
    expansion.

    The idea is based off of numpy ndarrays.

    @param new Number of new mail. Subset of unread.
    @param unread Number of unread mail. Subset of total.
    @param total Number of total mail.
    '''
    def __init__(self, new, unread, total):
        self.new = new
        self.unread = unread
        self.total = total

    def __repr__(self):
        return 'MailInfo(%d, %d, %d)' % (self.new, self.unread, self.total)
    
    def __str__(self):
        return 'MailInfo: %d new, %d unread, %d total' \
                     % (self.new, self.unread, self.total)

    def as_tuple(self):
        '''
        Returns the 3 numbers as a tuple. Useful for calculations directly on
        them.
        '''
        return (self.new, self.unread, self.total)


    def __gt__(self, other):
        '''
        Does a > comparison between all 3 numbers.

        @TODO Should this be a method, or is it alright as __gt__?
            A design issue (ie: indicating semantics).

        @return tuple of booleans (new_gt, unread_gt, total_gt).
        '''
        return (self.new > other.new,
                self.unread > other.unread,
                self.total > other.total)

    def __sub__(self, other):
        '''
        Does a subtraction between all 3 numbers.

        @return new MailInfo object with the new, unread, total numbers being
        self's - other's numbers.
        '''
        return MailInfo(self.new - other.new,
                        self.unread - other.unread,
                        self.total - other.total)


def get_number_mail():
    '''
    This function is dependent on what mail client you use. I use claws and to
    keep it simple, I just hard-coded it.

    @return MailInfo if was able to get the data. None if not.
    '''
    data = subprocess.check_output(['claws-mail', '--status'],
                                    universal_newlines=True)

    if data.strip() == CLAWS_MAIL_NOT_RUNNING:
        return None

    data = tuple(map(int, data.split()))
    return MailInfo(data[0], data[1], data[2])


def notify(diff_new, diff_unread):
    '''
    Notifies user.

    @note
    Keeping simple for now and hard coding to just use notify-send (actually using pynotify2).
    '''
    msg = '%d new and %d unread mail arrived' % (diff_new, diff_unread)

    # TODO: icon?
    notif = notify2.Notification('New Mail', msg)
    notif.set_category('email.arrived')
    # TODO: urgency?
    notif.show()


def main():
    '''
    Main function.

    Loop which continuously checks the number of new/unread messages and
    notifies if either increases.
    '''
    notify2.init('mail_notifier')

    prev_number = None

    while True:
        curr_number = get_number_mail()

        if not(prev_number is None or curr_number is None):
            if any((curr_number > prev_number)[:2]):
                diff_number = curr_number - prev_number

                # TODO: computation is incorrect as new mail is counted twice
                #  once for new, once for unread
                diff_new = max(0, diff_number.new)
                diff_unread = max(0, diff_number.unread)

                notify(diff_new, diff_unread)

        prev_number = curr_number
        time.sleep(SLEEP_TIME)


if __name__ == '__main__':
    main()

