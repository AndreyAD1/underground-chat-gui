import logging


logger = logging.getLogger('sender')
logger.setLevel(logging.DEBUG)
for handler in logger.handlers:
    logger.removeHandler(handler)

console = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
console.setFormatter(formatter)
logger.addHandler(console)
