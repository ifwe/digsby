#define CHECKSUM_EMPTY 0xffff0000L


class OFTChecksum {


};

    /** The checksum value. */
    private long checksum;

    { // init
        reset();
    }

    /**
     * Creates a new file transfer checksum computer object.
     */
    public FileTransferChecksum() { }

    public void update(int value) {
        update(new byte[] { (byte) value }, 0, 1);
    }

    public void update(final byte[] input, final int offset, final int len) {
        DefensiveTools.checkNull(input, "input");

        assert checksum >= 0;

        long check = (checksum >> 16) & 0xffffL;

        for (int i = 0; i < len; i++) {
            final long oldcheck = check;

            final int byteVal = input[offset + i] & 0xff;

            final int val;
            if ((i & 1) != 0) val = byteVal;
            else val = byteVal << 8;

            check -= val;

            if (check > oldcheck) check--;
        }

        check = ((check & 0x0000ffff) + (check >> 16));
        check = ((check & 0x0000ffff) + (check >> 16));

        checksum = check << 16 & 0xffffffffL;
        assert checksum >= 0;
    }

    public long getValue() {
        assert checksum >= 0;
        return checksum;
    }

    public void reset() {
        checksum = CHECKSUM_EMPTY;
        assert checksum >= 0;
    }

    public String toString() {
        return "FileTransferChecksum: " + checksum;
    }
}