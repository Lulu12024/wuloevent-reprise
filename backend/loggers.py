import logging
from datetime import datetime

import json_log_formatter
import pytz
import sqlparse
from django.utils.timezone import now
from pygments import highlight
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers.sql import SqlLexer


class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    def json_record(self, message: str, extra: dict, record: logging.LogRecord):
        extra['name'] = record.name
        extra['filename'] = record.filename
        extra['funcName'] = record.funcName
        extra['msecs'] = record.msecs
        if record.exc_info:
            extra['exc_info'] = self.formatException(record.exc_info)

        return {
            'message': message,
            'timestamp': now(),
            'level': record.levelname,
            'context': extra
        }


class SqlFormatter(logging.Formatter):
    """
    Format and syntax highlight SQL queries for the terminal
    """

    def format(self, record):
        try:
            sql = sqlparse.format(
                record.sql,
                keyword_case='upper',
                identifier_case='lower',
                truncate_strings=50,
                reindent=True).strip('\n')
            sql = '\n\t| '.join([l for l in sql.split('\n')])
            sql = highlight(sql, SqlLexer(), TerminalFormatter())
            # Get the timezone object for New York
            tz = pytz.timezone('Africa/Porto-Novo')
            dt = datetime.now(tz)
            return 'OK {} | ({:.3f}) | {}'.format(dt.strftime("%m/%d/%Y, %H:%M:%S"), record.duration, sql)
        except:
            # fall back to the default formatting if anything happens
            return super().format(record)
