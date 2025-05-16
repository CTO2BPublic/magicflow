class RetryableError(Exception):

    def __repr__(self):
        return '%s: An unspecified retryable error has occurred; %s' % (self.__class__.__name__,
                                                                        self.args)


class PermanentError(Exception):

    def __repr__(self):
        return '%s: An unspecified permanent error has occurred; %s' % (self.__class__.__name__,
                                                                        self.args)


class QueueAuthError(PermanentError):

    def __repr__(self):
        return '%s: Queue driver authentication error; %s' % (self.__class__.__name__, self.args)


class QueueConnectionError(RetryableError):

    def __repr__(self):
        return '%s: Queue driver connection error; %s' % (self.__class__.__name__, self.args)


class InvalidMessageFormat(PermanentError):

    def __repr__(self):
        return '%s: Invalid message format error; %s' % (self.__class__.__name__, self.args)
