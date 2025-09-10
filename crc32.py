#!python3
"""
Utility to calculate crc32, or insert values into a file to help
force CRC to known outputs.
Inserted value can be autocreated, or provided as a parameter.

Examples:
Analogus to `cksum -a crc32b filename``` but with hex output instead of decimal.

```
$ python crc32.py -c filename
ebcd12aa
$ cksum -a crc32b test-zero.bin --raw | hexdump -C
00000000  74 eb 82 c0                                       |t...|
00000004
$ python crc32.py -c test-zero.bin --raw | hexdump -C
00000000  74 eb 82 c0                                       |t...|
00000004
```

```
$ dd if=/dev/zero of=test-zero.bin bs=16 count=1
$ python crc32.py --insert cafecafe --position -8 test-zero.bin
cafecafe
$ hexdump -C test-zero.bin 
00000000  00 00 00 00 00 00 00 00  ca fe ca fe 00 00 00 00  |................|
00000010
```

SPDX-License-Identifier: MIT OR Apache-2.0 OR ISC OR BSD-2-Clause OR GPL-2.0-or-later OR LGPL-2.0-or-later
Karl Palsson <karl.palsson@marel.com>
"""

import argparse
import os
import random
import sys
import zlib

def crc32(filename, chunksize=65536):
    """Compute the CRC-32 checksum of the contents of the given filename"""
    with open(filename, "rb") as f:
        checksum = 0
        while (chunk := f.read(chunksize)) :
            checksum = zlib.crc32(chunk, checksum)
        return checksum

def hex_string_32bit(s: str):
    if len(s) > 8:
        raise ValueError("Only 32bit hex is supported, 4 hex bytes, eg 'aabbccdd'")
    return int(s, 16)

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("filename")
p.add_argument("-r", "--raw", action="store_true", help="Output in raw binary, bigendian, for use with dd directly.", dest="binary")
p.add_argument("-c", "--check", help="Calculate the CRC over the file", action="store_true", default=False)
p.add_argument("--insert-random-at", help="insert a random, non-zero 32bit number at this position in the file (negative counts from end)", type=int, dest="index_random", required=False)
p.add_argument("-v", "--verbose", help="Verbose mode.  Unless set, output will be terse, designed for immediate consumption by other scripts!", action="store_true", default=False)
p.add_argument("--insert", help="Insert the provided hex string into the file", metavar="INSERTED", required=False, type=hex_string_32bit)
p.add_argument("-p", "--position", help="positition to insert INSERTED at. negative to count from end of file.", required=False, type=int)

def do_main(opts):
    if opts.check:
        answer = crc32(opts.filename)
        if opts.verbose:
            print(f"CRC32 of {opts.filename} is: {answer:08x}")
        if opts.binary:
            sys.stdout.buffer.write(answer.to_bytes(4))
        else:
            print(f"{answer:08x}")
        return

    if opts.index_random:
        opts.position = opts.index_random
        # Ensure a non-zero "crc" so that firmware knows if it has been inserted.
        opts.insert = int(random.randint(1, 2**32-1))

    if opts.insert and opts.position:
        with open(opts.filename, "r+b") as f:
            if opts.position >= 0:
                f.seek(opts.position, os.SEEK_SET)
            else:
                f.seek(opts.position, os.SEEK_END)
            # This writes the crc as big endian, just be aware of that when reading in firmware.
            f.write(opts.insert.to_bytes(4, signed=False))
            if opts.verbose:
                print(f"Wrote target selected CRC32 of {opts.insert:08x} to {opts.filename} at position: {opts.position}")
            print(f"{opts.insert:08x}")
        return

opts = p.parse_args()
do_main(opts)
