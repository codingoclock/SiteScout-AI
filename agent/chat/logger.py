import logging
import sys


class Logger:
    @staticmethod
    def setup():
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
