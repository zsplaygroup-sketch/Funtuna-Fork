#ifndef SD_CEARA_PROGRESS_BAR_H
#define SD_CEARA_PROGRESS_BAR_H

typedef void (*SdCearaDrawRect)(int left, int top, int right, int bottom,
                               unsigned char red, unsigned char green,
                               unsigned char blue);

static inline void sdCearaDrawProgressBar(unsigned int percent, SdCearaDrawRect draw)
{
    if (percent > 100)
        percent = 100;

    const int fill = (352 * percent) / 100;
    draw(192, 278, 552, 311, 27, 127, 74);
    draw(194, 280, 550, 309, 218, 174, 51);
    draw(196, 282, 548, 307, 5, 26, 17);
    if (fill > 0) {
        draw(197, 283, 197 + fill, 306, 16, 222, 99);
        draw(197 + fill, 283, 197 + fill, 306, 234, 203, 85);
    }
}

#endif
