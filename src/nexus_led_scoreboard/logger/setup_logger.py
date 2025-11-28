def get_logger():
    import logging
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger("nexus")
