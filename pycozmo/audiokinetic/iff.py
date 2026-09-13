"""
Minimal IFF/RIFF chunk reader.

Replaces the standard library's `chunk` module, which PEP 594 removed in Python
3.13. Only the small surface soundbank.py needs is implemented: construct from a
file object, read the name and size, read within the chunk, and skip to its end.

Vendored rather than taken as a dependency so that the supported Python range
depends on nothing outside this package.
"""

import struct
from typing import BinaryIO

__all__ = ["Chunk"]

HEADER_SIZE = 8


class Chunk:
    """One IFF chunk: a four-byte name, a length, and that many bytes of data.

    Raises EOFError when the file has no complete chunk header left, which is
    how callers detect the end of a bank.
    """

    def __init__(self, file: BinaryIO, align: bool = True, bigendian: bool = True,
                 inclheader: bool = False) -> None:
        self.closed = False
        self.align = align
        self.file = file

        header = file.read(HEADER_SIZE)
        if len(header) < HEADER_SIZE:
            raise EOFError
        self.chunkname = header[:4]

        fmt = ">L" if bigendian else "<L"
        try:
            self.chunksize = struct.unpack_from(fmt, header, 4)[0]
        except struct.error:
            raise EOFError from None
        if inclheader:
            self.chunksize -= HEADER_SIZE

        self.size_read = 0
        try:
            self.offset = self.file.tell()
        except (AttributeError, OSError):
            self.seekable = False
        else:
            self.seekable = True

    def getname(self) -> bytes:
        return self.chunkname

    def getsize(self) -> int:
        return self.chunksize

    def close(self) -> None:
        if not self.closed:
            try:
                self.skip()
            finally:
                self.closed = True

    def tell(self) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self.size_read

    def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if self.size_read >= self.chunksize:
            return b""
        if size < 0 or size > self.chunksize - self.size_read:
            size = self.chunksize - self.size_read

        data = self.file.read(size)
        self.size_read += len(data)
        # An odd-length chunk is followed by a pad byte that is not part of it.
        if self.size_read == self.chunksize and self.align and (self.chunksize & 1):
            pad = self.file.read(1)
            self.size_read += len(pad)
        return data

    def skip(self) -> None:
        """Advance to the end of the chunk, ready for the next one."""
        if self.closed:
            raise ValueError("I/O operation on closed file")

        remaining = self.chunksize - self.size_read
        if self.align and (self.chunksize & 1):
            remaining += 1

        if self.seekable:
            try:
                self.file.seek(remaining, 1)
                self.size_read += remaining
                return
            except OSError:
                pass

        while self.size_read < self.chunksize:
            block = self.read(min(8192, self.chunksize - self.size_read))
            if not block:
                raise EOFError
