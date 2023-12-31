import sys
from unittest.mock import patch

import pytest

from keycode_parser.boot import Boot


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stdin_contract", "stdin_retval", "stdout_contract", "expected_stdout"),
    (
        # any-txt
        # ---
        (
            "txt",
            "c.p.m.t.v1,c.p.m.t.v2",
            "txt",
            "c.p.m.t.v2,c.p.m.t.v1",
        ),
        (
            "py",
            "@code(\"c.p.m.t.v1\") @code(\"c.p.m.t.v2\")",
            "txt",
            "c.p.m.t.v2,c.p.m.t.v1",
        ),
        (
            "ts",
            "@code(\"c.p.m.t.v1\") @code(\"c.p.m.t.v2\")",
            "txt",
            "c.p.m.t.v2,c.p.m.t.v1",
        ),
        # ---

        # any-py
        # ---
        (
            "txt",
            "c.p.m.t.v1,c.p.m.t.v2",
            "py",
            """class Codes:
    class c:
        class p:
            class m:
                class t:
                    v2 = "c.p.m.t.v2"
                    v1 = "c.p.m.t.v1"
""",
        ),
        (
            "py",
            "@code(\"c.p.m.t.v1\") @code(\"c.p.m.t.v2\")",
            "py",
            """class Codes:
    class c:
        class p:
            class m:
                class t:
                    v2 = "c.p.m.t.v2"
                    v1 = "c.p.m.t.v1"
""",
        ),
        (
            "ts",
            "@code(\"c.p.m.t.v1\") @code(\"c.p.m.t.v2\")",
            "py",
            """class Codes:
    class c:
        class p:
            class m:
                class t:
                    v2 = "c.p.m.t.v2"
                    v1 = "c.p.m.t.v1"
""",
        ),
        # ---

        # any-ts
        (
            "txt",
            "c.p.m.t.v1,c.p.m.t.v2",
            "ts",
            """export default abstract class Codes {
  public static c = {
    p: {
      m: {
        t: {
          v2: "c.p.m.t.v2",
          v1: "c.p.m.t.v1",
        },
      },
    },
  };
};
""",
        ),
        (
            "py",
            "@code(\"c.p.m.t.v1\") @code(\"c.p.m.t.v2\")",
            "ts",
            """export default abstract class Codes {
  public static c = {
    p: {
      m: {
        t: {
          v2: "c.p.m.t.v2",
          v1: "c.p.m.t.v1",
        },
      },
    },
  };
};
""",
        ),
        (
            "ts",
            "@code(\"c.p.m.t.v1\") @code(\"c.p.m.t.v2\")",
            "ts",
            """export default abstract class Codes {
  public static c = {
    p: {
      m: {
        t: {
          v2: "c.p.m.t.v2",
          v1: "c.p.m.t.v1",
        },
      },
    },
  };
};
""",
        ),
    ),
)
async def test_stdin_stdout(
    stdin_contract: str,
    stdin_retval: str,
    stdout_contract: str,
    expected_stdout: str,
):
    original_stdout_write = sys.stdout.write
    global res  # noqa: PLW0602

    def stdout_write_mock(s: str) -> int:
        global res  # noqa: PLW0603
        res = s
        return original_stdout_write(s)

    with patch.object(sys.stdin, "read", return_value=stdin_retval):
        sys.stdout.write = stdout_write_mock
        await Boot.from_cli(
            ["@stdin:" + stdin_contract],
            ["@stdout:" + stdout_contract],
        ).start()

        # remove mock for possible print-debug without surprises
        sys.stdout.write = original_stdout_write
        assert res == expected_stdout


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pathstrs", "stdout_contract", "expected_codes"),
    (
        (
            (
                "./tests/globs/**/*.ts",
            ),
            "txt",
            (
                "c.p.m.t.v1",
                "c.p.m.t.v2",
                "c.p.m.t.v3",
                "c.p.m.t.v4"
            ),
        ),
    )
)
async def test_globs(
    pathstrs: tuple[str],
    stdout_contract: str,
    expected_codes: tuple[str],
):
    original_stdout_write = sys.stdout.write
    global res  # noqa: PLW0602

    def stdout_write_mock(s: str) -> int:
        global res  # noqa: PLW0603
        res = s
        return original_stdout_write(s)

    sys.stdout.write = stdout_write_mock
    await Boot.from_cli(
        pathstrs,
        ["@stdout:" + stdout_contract],
    ).start()

    # remove mock for possible print-debug without surprises
    sys.stdout.write = original_stdout_write
    assert set(res.split(",")) == set(expected_codes)
