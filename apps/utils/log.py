import logging
from inspect import getframeinfo, stack
from logging.handlers import RotatingFileHandler


class CallerFilter(logging.Filter):
    """ This class adds some context to the log record instance """
    file = ''
    line_n = ''

    def filter(self, record):
        record.file = self.file
        record.line_n = self.line_n
        return True


def caller_reader(f):
    """This wrapper updates the context with the callor infos"""

    def wrapper(self, *args):
        caller = getframeinfo(stack()[1][0])
        self._filter.file = caller.filename
        self._filter.line_n = caller.lineno
        return f(self, *args)

    return wrapper


class Log:

    def __init__(self, path):
        self.LOGGER = logging.getLogger('Open-Capture')
        if self.LOGGER.hasHandlers():
            self.LOGGER.handlers.clear()  # Clear the handlers to avoid double logs
        logFile = RotatingFileHandler(path, mode='a', maxBytes=5 * 1024 * 1024,
                                      backupCount=2, encoding=None, delay=0)
        formatter = logging.Formatter(
            '[%(threadName)-14s] [%(file)s:%(line_n)-15s] %(asctime)s %(levelname)s %(message)s',
            datefmt='%d-%m-%Y %H:%M:%S')
        logFile.setFormatter(formatter)
        self.LOGGER.addHandler(logFile)
        # Here we add the Filter, think of it as a context
        self._filter = CallerFilter()
        self.LOGGER.addFilter(self._filter)
        self.LOGGER.setLevel(logging.DEBUG)

    @caller_reader
    def info(self, msg):
        self.LOGGER.info(msg)

    @caller_reader
    def error(self, msg):
        self.LOGGER.error(msg)
