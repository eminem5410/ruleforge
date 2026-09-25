class ParserError(Exception):
    def __init__(self, code, message, line, column):
        self.code = code
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{code} Parse Error: {message} at Line {line}, Column {column}")
