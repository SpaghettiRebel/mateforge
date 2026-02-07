class TokenError(Exception):
    pass

class TokenExpiredError(TokenError):
    pass

class TokenInvalidError(TokenError):
    pass


class UserError(Exception):
    pass


class UserDoesNotExist(UserError):
    pass