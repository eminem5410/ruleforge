class SemanticError(Exception):
    def __init__(self, code, message, line=0, column=0):
        self.code = code
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{code} Semantic Error: {message}")
