#!/usr/bin/python3.3
'''
Simple script which notifies user when a new mail comes in.

Works by keeping track of unread mail and notifying user when it increases.

Requires python3.3 because it uses the subprocess timeouts, which was added in
python3.3.

TODO: program arguments
    config file?

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


# constants
SLEEP_TIME = 10
MAIL_INFO_TIMEOUT = 5       # should return in < 1 second, but we're in no rush.

# msg claws-mail output when its not running. Unlikely to change, but could.
CLAWS_MAIL_NOT_RUNNING = '0 Claws Mail not running.'


#
## Exceptions
#

class NoDataException(Exception):
    '''
    Exception indicating no data was found.
    '''
    pass

#
## Logging
#

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

    Sometimes the data returned from the subprocess call will be just an empty
    string. IE: we have no idea whether the program is running or how many
    emails there are. I feel the best approach in this case is to simply skip
    this iteration of the loop. To do this, we throw an NoDataException.

    If the subprocess call times out, just assume no data returned. Ie skip
    this iteration and try again later.

    TODO: data validation?

    @return MailInfo if was able to get the data. None if not.
    '''
    try:
        orig_data = subprocess.check_output(['claws-mail', '--status'],
                                    universal_newlines=True,
                                    timeout=MAIL_INFO_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        logger.error('Subprocess call to %s timed out after %d seconds. Data retrieved thus far is %s, but cannot use it.', e.cmd, e.timeout, e.output)
        orig_data = ''

    data = orig_data.strip()

    if len(data) == 0:
        logger.error('data is empty string, raising NoDataException')
        raise NoDataException

    if data == CLAWS_MAIL_NOT_RUNNING:
        return None

    int_data = tuple(map(int, data.split()))
    try:
        return MailInfo(int_data[0], int_data[1], int_data[2])
    except IndexError as e:
        logger.exception('Exiting b/c data malformed')
        logger.error("orig_data: '%s', data: '%s', int_data: '%s'" % (str(orig_data), str(data), str(int_data)))
        quit(1)     # TODO: exit-code


def notify(diff_new, diff_unread):
    '''
    Notifies user.

    @note
    Keeping simple for now and hard coding to just use notify-send (actually using pynotify2).

    @return Bool indicating whether the notification was sucessful. True = Succesful.
    '''
    msg = '%d new and %d unread mail arrived' % (diff_new, diff_unread)

    # TODO: icon?
    # TODO: urgency?

    try:
        subprocess.check_call(['notify-send', '-c', 'email.arrived', 'New Mail', msg])
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
    prev_number = None

    while True:
        # if there's no data, recycle the previous number so as to prevent us
        # from doing anything this loop.
        try:
            curr_number = get_number_mail()
        except NoDataException:
            logger.info('Caught NoDataException, so recycling previous numbers.')
            curr_number = prev_number

        one_is_None = prev_number is None or curr_number is None

        notification_failed = False
        if not one_is_None:
            if any((curr_number > prev_number)[:2]):
                diff_number = curr_number - prev_number

                # computation is incorrect as new mail is counted twice once
                #  for new, once for unread. So unread = unread - new.
                diff_new = max(0, diff_number.new)
                diff_unread = max(0, diff_number.unread)
                diff_unread = diff_unread - diff_new

                notification_failed = not notify(diff_new, diff_unread)

        if not notification_failed:
            prev_number = curr_number
            
        time.sleep(SLEEP_TIME)


# version check for python > 3.3, for subprocess timeout feature.
def version_check():
    '''
    Checks version information on python.
    '''
    if not (sys.version_info.major, sys.version_info.minor) >= (3, 3):
        msg = 'Current python version is %d.%d, version 3.3 required. Quiting.' % (sys.version_info.major, sys.version_info.minor)
        logger.fatal(msg)
        print(msg)
        quit()


def main():
    '''
    Main function.
    
    Simply an outside wrapper around the workhorse function. Serves to catch
    all exception and do logging stuff.
    '''
    try:
        logger.info('Starting')

        version_check()

        mail_notifier()

    except KeyboardInterrupt:
        logger.info('Received Ctrl-C, so quiting')
    except Exception as e:
        logger.exception('Quitting due to unhandled exception')


if __name__ == '__main__':
    main()


