import re
import keyword
import tokenize

from pytest_flakefriend.base import Base


CAMEL_CASE_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)")


class GetTokens(Base):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.tokens = set()

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or ignore into token values (null, ?)",
            [(token,) for token in self.tokens]
        )

        cur.execute("select token, id from token")
        self.token_to_id = dict(cur.fetchall())

    def get_tokens(self, readline, lines=None):
        tokens = set()

        for type, token, (line, _), *_ in tokenize.tokenize(readline):
            if type != tokenize.NAME or keyword.iskeyword(token) or (
                lines is not None and line not in lines
            ):
                continue
                
            tokens.add(token.lower())

            for sub_token in token.split("_"):
                for sub_sub_token in CAMEL_CASE_RE.findall(sub_token):
                    tokens.add(sub_sub_token.lower())

        self.tokens.update(tokens)
        return tokens