import io
import sqlite3

from pytest_flakefriend.get_tokens import GetTokens


def test_save(db_file):
    plugin = GetTokens(db_file, 1, 1)
    plugin.mode = 0
    plugin.tokens = {"foo", "bar", "baz"}
    
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        plugin.save(cur)
        cur.execute("select * from token")

        assert set(cur.fetchall()) == {
            (plugin.token_to_id["foo"], "foo"),
            (plugin.token_to_id["bar"], "bar"), 
            (plugin.token_to_id["baz"], "baz"),
        }


def test_get_tokens():
    plugin = GetTokens(None, None, None)

    source = (
        "class FooBar_baz:\n"
        "    def x_y(a, b):\n"
        "        c = 2 * a + b\n"
        "        d = 3 * c\n"
        "        e = 4 * d\n"
        "        return c + d\n"
    )

    readline = io.BytesIO(source.encode("utf-8")).readline

    assert plugin.get_tokens(readline, {1, 2, 3, 4, 6}) == {
        "foobar_baz", "foo", "bar", "baz", "x_y", "x", "y", "a", "b", "c", "d"
    }