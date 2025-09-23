from vagabond.config import app_config

import logging

def setup_logger(log):
    log.setLevel(app_config.console_log_level)

    # because of the nature of flask and how it auto reloads, it could be adding duplicate handlers
    if not log.hasHandlers():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(CustomFormatter())

        file_handler = logging.FileHandler("app.log")
        file_handler.setLevel(app_config.file_log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
        )
        file_handler.setFormatter(file_formatter)

        log.addHandler(console_handler)
        log.addHandler(file_handler)

class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    light_blue = "\x1b[94;20m"
    light_green = "\x1b[92;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: light_blue + format_str + reset,
        logging.INFO: light_green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        # format exceptions as well
        if record.exc_info:
            log_fmt = self.FORMATS.get(record.levelno, self.format_str)
            formatter = logging.Formatter(log_fmt)
            base = formatter.format(record)
            return f"{base}\n{self.formatException(record.exc_info)}"
        else:
            log_fmt = self.FORMATS.get(record.levelno, self.format_str)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)