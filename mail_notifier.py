#!/usr/bin/python3
'''
Simple script which notifies user when a new mail comes in.

Works by keeping track of unread mail and notifying user when it increases.

TODO: license (GPL v. 3)

TODO: handle case where mail client not running
    so can't get numbers from it

TODO: program arguments
    config file?

TODO: handle import errors for notify2?
    Continue running and use another method vs quiting?

TODO: logging?

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


class mail_info:
    '''
    Probably overkill, but made it cleaner IMO. Could also use numpy ndarrays,
    but that's way overkill. And is a completely unnecessary dependency.

    The idea is based off of numpy ndarrays. We may expand this to do more
    stuff later too.
    '''
    def __init__(self, new, unread, total):
        self.new = new
        self.unread = unread
        self.total = total

    def __repr__(self):
        return 'mail_info(%d, %d, %d)' % (self.new, self.unread, self.total)
    
    def __str__(self):
        return 'mail_info: %d new, %d unread, %d total' % (self.new, self.unread, self.total)

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

        @return tuple of bools (new_gt, unread_gt, total_gt).
        '''
        return (self.new > other.new,
                self.unread > other.unread,
                self.total > other.total)

    def __sub__(self, other):
        '''
        Does a subtraction between all 3 numbers.

        @return new mail_info object with the new, unread, total numbers being
        self's - other's numbers.
        '''
        return mail_info(self.new - other.new,
                        self.unread - other.unread,
                        self.total - other.total)


def get_number_mail():
    '''
    This function is dependent on what mail client you use. I use claws and to
    keep it simple, I just hard-coded it.

    @return mail_info if was able to get the data. None if not.
    '''
    data = subprocess.check_output(['claws-mail', '--status'], universal_newlines=True)

    if data.strip() == CLAWS_MAIL_NOT_RUNNING:
        return None

    data = tuple(map(int, data.split()))
    return mail_info(data[0], data[1], data[2])


def notify(diff_new, diff_unread):
    '''
    Notifies user.

    @note
    Keeping simple for now and hard coding to just use notify-send (actually using pynotify2).
    '''
    msg = '%d new and %d unread mail arrived' % (diff_new, diff_unread)

    # TODO: icon?
    n = notify2.Notification('New Mail', msg)
    n.set_category('email.arrived')
    # TODO: urgency?
    n.show()


def main():
    notify2.init('mail_notifier')

    prev_number = None

    while True:
        curr_number = get_number_mail()

        if not(prev_number is None or curr_number is None):
            if any((curr_number > prev_number)[:2]):
                diff_number = curr_number - prev_number
                diff_new = max(0, diff_number.new)
                diff_unread = max(0, diff_number.unread)

                notify(diff_new, diff_unread)

        prev_number = curr_number
        time.sleep(SLEEP_TIME)


if __name__ == '__main__':
    main()

