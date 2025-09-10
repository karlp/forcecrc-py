## forcecrc32.py - Forcing CRC32 in python
`forcecrc32.py` is a straight fork of https://www.nayuki.io/page/forcing-a-files-crc-to-any-value

It has a single trivial change to support negative offsets to count from the end of the file.

It is provided here as a reference, not in anyway intended to be the canonical source.

## crc32.py - calculate crc32 or insert into files
Can calculate a crc32 (just like cksum -a crc32b or zlib et al)
Can also insert random/specified values into a file at a given offset.

Has it's own help, see `python crc32.py -h`

## Goals/Usage
Goal is to have a binary firmware, with a checksum embedded in the file, but
with the calculated checksum of that file being that same checksum.
This means "standard" tools can check the file and determine the same checksum, but that
some embedded firmware can also access this checksum for validation.
It is _only_ intended for "protection against accidental corruption" as any checksum.
It is, after all, just a checksum!

The method is to _choose_ a CRC value ahead of time, write that into the file, and then use
maths to write another four bytes into the file to make the CRC of the entire file match
the _chosen_ CRC.

Note, the examples below place these 8 bytes (4 bytes chosen crc plus 4 bytes used to force the 
maths) at the end of the application binary image. (The end of .data) You don't have to put it
there, you just need to have your own stable place for it to be.

### In your C source...
```C
struct fwinfo_block {
	uint32_t crc32_be;
	uint32_t pad_bytes;
};

 /**
 * This block is placed at the _end_ of our image by linker scripts.
 * The build process then selects a random non-zero crc32, writes it to the CRC32,
 * and mathematically forces the pad_bytes to ensure the correct final CRC.
 * If the crc32 field is still 0, you are running from the original .elf, not a factory
 * produced production binary.
 */
__attribute__((used, section(".fw_crc_info")))
struct fwinfo_block fw_crc_info = {0, 0};

/**
 * Remember, the host tools write in big endian to make it easier to compare for humans.
 */
uint32_t fwinfo_crc_img(void)
{
	return __builtin_bswap32(fw_crc_info.crc32_be);
}

uint32_t fwinfo_do_crc(void)
{
	uint32_t calc_crc = 0;
	for (uint32_t *p = &_image_start; p < &_image_end; p++) {
        calc_crc = your_crc_routine_update_call(*p);
	}
    return calc_crc;
}

```


### In your linker scripts...
You need to snag that `.fw_crc_info` section to the _end of data_
(or, anywhere you prefer really, but you need to know where it is so you can modify it later.
This is a simplified extract, not an entire linker script.
```ld
.data: ALIGN(4)
{
    _data = .
    *(.data*)
    KEEP(*(.fw_crc_info))
    _edata = .
}> RAM AT>FLASH
...
    _image_start = LOADADDR(.text);
    _image_end = LOADADDR(.data) + SIZEOF(.data);
...

```

### In your build scripts....
Something like this, adjust the position to suit what you did with your own linker scripts.
```cmake

# Ensure crc is never 0
string(RANDOM LENGTH 8 ALPHABET 123456789abcdef CRC_ASSIGNED)

add_custom_target(
    ${binary_name}_crc ALL
    COMMENT "Assigning CRC of ${CRC_ASSIGNED} to ${binary_name}_crc"
    COMMAND ${CMAKE_COMMAND} -E copy ${binary_name} ${binary_name}_crc
    COMMAND ${Python3_EXECUTABLE} crc32.py --insert ${CRC_ASSIGNED} --position -8 ${binary_name}_crc
    COMMAND ${Python3_EXECUTABLE} forcecrc32.py ${binary_name}_crc -4 ${CRC_ASSIGNED}
    DEPENDS ${binary_name}
)

add_dependencies(release ${binary_name}_crc)
```
