import ast
import sys

import radon
import pytest
import coverage

from pytest_flakefriend.static import (
    get_func_node_bodies, get_statement_depth, get_external_modules
)


def test_get_func_node_bodies():
    source_lines = [
        "def foo():\n",
        "    x = a + b\n",
        "    return x\n",
        "@decorator\n",
        "def bar(\n",
        "    x, y, z\n",
        "):\n",
        "    a = x * y\n",
        "    b = (\n",
        "        a - z\n",
        "    )\n",
        "    if b:\n",
        "        print('hi')\n",
        "    return b\n",
        "\n",
        "class Baz:\n",
        "    def __init__(self, a, b, c, d):\n",
        "        self.x = a * b\n",
        "        self.y = c * d\n",
        "        self.z = \"\"\"\n",
        "foo\"\"\"\n",
        "        return 0\n",
        "    def qux(x, y, z, w): return bar(\n",
        "        x, y, z, 0)\n",
        "\n",
        "\n",
        "@decorator1\n",
        "@decorator2\n",
        "def quz(\n",
        "    *x, **y): return 0\n",
    ]

    func_node_bodies = get_func_node_bodies(source_lines)
    assert set(func_node_bodies) == {1, 4, 17, 23, 27}

    assert func_node_bodies[1][1] == (
        "x = a + b\n"
        "return x\n"
    )

    assert func_node_bodies[4][1] == (
        "a = x * y\n"
        "b = (\n"
        "    a - z\n"
        ")\n"
        "if b:\n"
        "    print('hi')\n"
        "return b\n"
    )

    assert func_node_bodies[17][1] == (
        "self.x = a * b\n"
        "self.y = c * d\n"
        "self.z = \"\"\"\n"
        "foo\"\"\"\n"
        "return 0\n"
    )

    assert func_node_bodies[23][1] == (
        "return bar(\n"
        "    x, y, z, 0)\n"
    )

    assert func_node_bodies[27][1] == (
        "return 0\n"
    )


@pytest.mark.parametrize(
    "source,expected", 
    [
        (
            "a = foo()\n",
            1
        ),
        (
            "if bar():\n"
            "    a = foo()\n",
            2
        ),
        (
            "for x in bar():\n"
            "    if bar():\n"
            "        a = foo()\n",
            3
        ),        
        (
            "while baz():\n"
            "    if bar():\n"
            "        a = foo()\n"
            "    for x in bar():\n"
            "        if bar():\n"
            "            a = foo()\n",
            4
        )
    ]
)
def test_get_statement_depth(source, expected):
    assert get_statement_depth(ast.parse(source).body[0]) == expected


@pytest.mark.parametrize(
    "source,varnames,expected", 
    [
        (
            "import pytest\n"
            "import coverage\n",
            [],
            {"coverage"}
        ),
        (
            "import pytest_flakefriend\n"
            "from coverage import Coverage\n",
            [],
            {"coverage"}
        ),
        (
            "foo = radon.metrics.mi_parameters(foo)\n"
            "bar = ast.parse(bar)\n",
            [],
            {"radon"}
        ),
        (
            "foo = radon.metrics.mi_parameters(foo)\n"
            "bar = ast.parse(bar)\n"
            "baz = pytest_flakefriend.plugin.Plugin()\n",
            ["radon"],
            set()
        )
    ]
)
def test_get_external_modules(source, varnames, expected):
    module = sys.modules[__name__]
    output = set(get_external_modules(ast.parse(source), module, varnames))
    assert output == expected