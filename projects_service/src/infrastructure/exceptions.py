class TokenError(Exception):
    pass

class TokenExpiredError(TokenError):
    pass

class TokenInvalidError(TokenError):
    pass


class ExternalServiceUnavailable(Exception):
    pass
