class SchedulerError(Exception):
    pass


class ConfigError(SchedulerError):
    pass


class TrelloError(SchedulerError):
    pass
