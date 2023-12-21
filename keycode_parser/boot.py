import multiprocessing as mp
import sys
from multiprocessing import Process
from pathlib import Path
from typing import Callable, Literal, Self

from pykit import Log

from keycode_parser.codeparsers import CodeParser, TypescriptCodeParser
from keycode_parser.sources import (
    FilepathSource,
    Source,
    SourceContract,
    TextIOSource,
)
from keycode_parser.utils import CodeUtils


class Boot:
    _CodeParserByContract: dict[str, CodeParser] = {
        SourceContract.TXT.value: CodeParser(),
        SourceContract.TS.value: TypescriptCodeParser(),
    }

    def __init__(
        self,
        input_sources: list[Source],
        output_sources: list[Source],
    ) -> None:
        self._input_sources = input_sources
        self._output_sources = output_sources

    @classmethod
    def from_cli(cls, input_args: list[str], output_args: list[str]) -> Self:
        input_sources = cls._parse_sources(input_args, "input")
        output_sources = cls._parse_sources(output_args, "output")
        return cls(input_sources, output_sources)

    @classmethod
    def _parse_sources(
        cls, raw: list[str], mode: Literal["input", "output"],
    ) -> list[Source]:
        res: list[Source] = []

        for r in raw:
            if r.startswith("@"):
                res.append(cls._parse_special_raw_source(r, mode))
                continue
            path = Path(r)
            res.append(FilepathSource(
                source=path,
                contract=SourceContract(path.suffix.replace(".", "")).value,
            ))

        return res

    @classmethod
    def _parse_special_raw_source(
        cls,
        raw: str,
        mode: Literal["input", "output"],
    ) -> Source:
        """
        Special raw source - starts with "@".
        """
        if raw == "@stdin":
            raise ValueError(
                "specify stdin in format \"@stdin:<extension>\"",
            )
        elif raw.startswith("@stdin"):
            if mode == "output":
                raise ValueError(
                    "stdin source cannot appear in output",
                )
            _, raw_extension = raw.split(":")
            contract = SourceContract(raw_extension)
            return TextIOSource.model_construct(
                source=sys.stdin, contract=contract.value,
            )
        elif raw == "@stdout":
            if mode == "input":
                raise ValueError(
                    "stdout source cannot appear in input",
                )
            return TextIOSource.model_construct(
                source=sys.stdout,
                contract="txt",
            )
        else:
            raise ValueError(f"unrecognized raw source {raw}")

    async def start(self) -> None:
        codes: list[str] = self._collect_codes()
        if not codes:
            Log.info("no codes were collected")
            return
        self._write_codes(codes)

    def _collect_codes(self) -> list[str]:
        res: list[str] = []

        pool_res = []
        pool = mp.Pool()

        for source in self._input_sources:
            func: Callable = CodeUtils.search_for_codes
            args: tuple = (source.api,)

            pool_res.append(pool.apply(func, args))

        pool.close()
        pool.join()

        for pr in pool_res:
            if pr not in res:
                res.extend(pr)

        return res

    def _write_codes(self, codes: list[str]) -> None:
        # memoized contents, for now collected synchronously
        content_by_contract: dict[str, str] = {}
        processes: list[Process] = []

        for source in self._output_sources:
            if source.contract not in content_by_contract:
                content_by_contract[source.contract] = \
                    self._CodeParserByContract[source.contract].parse(codes)
            content = content_by_contract[source.contract]

            if isinstance(source, FilepathSource):
                p = Process(
                    target=self._write_to_output_file,
                    args=(
                        source.source,
                        content,
                    ),
                )
                p.start()
                processes.append(p)
            elif isinstance(source, TextIOSource):
                source.source.write(content)
            else:
                raise TypeError(f"unrecognized output source {source}")

        for p in processes:
            p.join()

    def _write_to_output_file(self, path: Path, content: str) -> None:
        # output file is always overwritten, path should be checked before that
        # it is truly an auto file
        with path.open( "w+") as f:
            f.write(content)
