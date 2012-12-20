#!/usr/bin/python3
'''
Simple script which notifies user when a new mail comes in.

Works by keeping track of unread mail and notifying user when it increases.

TODO: switch from notify2 library to calling notify-send via subprocesses?
    - notify2 seems to run into a dbus issue that prevents it from ever showing a
      message (after a certain point).
    - not clear how much support notify2 is going to have anyways. notify-send
      looks like it'll be supported for much much longer.
    - test on a branch

TODO: program arguments
    config file?

TODO: handle import errors for notify2?
    Continue running and use another method vs quiting?

TODO: more logging?

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
import logging
import logging.handlers
import subprocess
import sys
import time

# 3rd party modules
import notify2


# constants
SLEEP_TIME = 10

# msg claws-mail output when its not running. Unlikely to change, but could.
CLAWS_MAIL_NOT_RUNNING = '0 Claws Mail not running.'


def setup_logging(log_level = logging.DEBUG, address = '/dev/log'):
    '''
    Sets up the logging for the program.

    Returns the logger
    '''
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # syslog handler
    syslog_handler = logging.handlers.SysLogHandler(address = address)
    syslog_formater = logging.Formatter('%(module)s[%(process)d] - %(levelname)s: %(message)s')
    syslog_handler.setFormatter(syslog_formater)
    syslog_handler.setLevel(logging.INFO)           # don't send debug messages to syslog
    logger.addHandler(syslog_handler)

    # stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    logger.addHandler(stderr_handler)

    return logger

logger = setup_logging()


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

    @return Bool indicating whether the notification was sucessful. True = Succesful.
    '''
    msg = '%d new and %d unread mail arrived' % (diff_new, diff_unread)

    # TODO: icon?
    notif = notify2.Notification('New Mail', msg)
    notif.set_category('email.arrived')
    # TODO: urgency?

    # TODO: show() sometimes fails with a DBusException
    try:
        logger.debug('Calling show')
        notif.show()
    except Exception:
        logger.exception('Failed to show notification')
        return False

    return True


def mail_notifier():
    '''
    Workhorse function which detects mail and notifies us about it.

    Loop which continuously checks the number of new/unread messages and
    notifies if either increases.

    Will update prev_number in all cases except when notification fails
    '''
    notify2.init('mail_notifier')

    prev_number = None

    while True:
        curr_number = get_number_mail()

        one_is_None = prev_number is None or curr_number is None

        logger.debug('prev, curr = %s, %s' % (prev_number, curr_number))

        notification_failed = False
        if not one_is_None:
            if any((curr_number > prev_number)[:2]):
                diff_number = curr_number - prev_number

                # TODO: computation is incorrect as new mail is counted twice
                #  once for new, once for unread
                diff_new = max(0, diff_number.new)
                diff_unread = max(0, diff_number.unread)

                notification_failed = not notify(diff_new, diff_unread)

        if not notification_failed:
            prev_number = curr_number
            
        time.sleep(SLEEP_TIME)


def main():
    '''
    Main function.
    
    Simply an outside wrapper around the workhorse function. Serves to catch
    all exception and do logging stuff.
    '''
    try:
        logger.info('Starting')

        mail_notifier()

    except KeyboardInterrupt:
        logger.info('Received Ctrl-C, so quiting')
    except Exception as e:
        logger.exception('Quitting due to unhandled exception')


if __name__ == '__main__':
    main()


