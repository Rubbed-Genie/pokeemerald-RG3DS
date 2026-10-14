#include <3ds.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "3ds_platform.h"
#include "3ds_devmenu.h"

static CtrInput sInput;

/*
 * RG3DS debug driver: drive.txt next to settings.txt, read when it appears
 * and then deleted, plays its words as if from the pad - so a test can be run
 * on the desktop emulator without sending keys to the desktop. Words:
 *   up down left right a b start select l r x y [N][@F]  press N times
 *                  (default 1), each held F frames (default 6; a tile is 16)
 *   wait[N]        N frames (default 60)
 *   shot           dump the top screen (shot-<frame>.raw, CtrVideo)
 *   warp:G:N:X:Y   warp there (3ds_game_full.c)
 * A press holds 6 frames and lets go 6.
 */
static struct
{
    char text[1024];
    unsigned pos, polled;
    int hold, gap, wait, held;
    uint32_t bits;
    int repeat;
} sDrive;
volatile int gCtrDriveShot;
volatile int gCtrDriveWarp[4] = {-1, -1, -1, -1};

static uint32_t DriveStep(void)
{
    static const char *const names[] = {"a", "b", "select", "start", "right", "left", "up", "down",
                                        "r", "l", "x", "y", "zl", "zr", "zlzr"};

    if (sDrive.text[0] == 0 && ++sDrive.polled % 30 == 0)
    {
        FILE *file = CtrFs_OpenData("drive.txt", "r");

        if (file != NULL)
        {
            size_t n = fread(sDrive.text, 1, sizeof(sDrive.text) - 1, file);

            sDrive.text[n] = 0;
            fclose(file);
            remove("sdmc:/3ds/emerald3ds/drive.txt");
            sDrive.pos = 0;
        }
    }
    if (sDrive.wait > 0)
    {
        --sDrive.wait;
        return 0;
    }
    if (sDrive.hold > 0)
    {
        if (--sDrive.hold == 0)
            sDrive.gap = 6;
        return sDrive.bits;
    }
    if (sDrive.gap > 0)
    {
        --sDrive.gap;
        return 0;
    }
    if (sDrive.repeat > 0)
    {
        --sDrive.repeat;
        sDrive.hold = sDrive.held;
        return sDrive.bits;
    }
    while (sDrive.text[0] != 0)
    {
        char word[48];
        int len = 0, count = 1;
        unsigned i;

        while (sDrive.text[sDrive.pos] == ' ' || sDrive.text[sDrive.pos] == '\n' || sDrive.text[sDrive.pos] == '\r'
            || sDrive.text[sDrive.pos] == '\t')
            ++sDrive.pos;
        if (sDrive.text[sDrive.pos] == 0)
        {
            sDrive.text[0] = 0;
            break;
        }
        while (sDrive.text[sDrive.pos] > ' ' && len < (int)sizeof(word) - 1)
            word[len++] = sDrive.text[sDrive.pos++];
        word[len] = 0;
        if (strncmp(word, "warp:", 5) == 0)
        {
            int g, m, x, y;

            if (sscanf(word + 5, "%d:%d:%d:%d", &g, &m, &x, &y) == 4)
            {
                gCtrDriveWarp[1] = m; gCtrDriveWarp[2] = x; gCtrDriveWarp[3] = y;
                gCtrDriveWarp[0] = g;
            }
            sDrive.wait = 90;
            return 0;
        }
        if (strcmp(word, "shot") == 0)
        {
            gCtrDriveShot = 1;
            sDrive.wait = 10;
            return 0;
        }
        if (strncmp(word, "wait", 4) == 0)
        {
            sDrive.wait = word[4] ? atoi(word + 4) : 60;
            return 0;
        }
        {
            /* "down@64": held 64 frames, 16 a tile walking */
            char *at = strchr(word, '@');
            int held = 6;

            if (at != NULL)
            {
                held = atoi(at + 1);
                *at = 0;
                len = (int)(at - word);
                if (held <= 0)
                    held = 6;
            }
            sDrive.held = held;
        }
        while (len > 0 && word[len - 1] >= '0' && word[len - 1] <= '9')
            --len;
        if (word[len] != 0)
            count = atoi(word + len);
        word[len] = 0;
        for (i = 0; i < sizeof(names) / sizeof(names[0]); ++i)
            if (strcmp(word, names[i]) == 0)
                break;
        if (i == sizeof(names) / sizeof(names[0]) || count <= 0)
            continue;
        sDrive.bits = 1u << i;
        sDrive.repeat = count - 1;
        sDrive.hold = sDrive.held;
        return sDrive.bits;
    }
    return 0;
}

void CtrInput_Clear(void)
{
    memset(&sInput, 0, sizeof(sInput));
}

void CtrInput_Scan(void)
{
    static const uint32_t keys[] =
    {
        KEY_A, KEY_B, KEY_SELECT, KEY_START, KEY_DRIGHT,
        KEY_DLEFT, KEY_DUP, KEY_DDOWN, KEY_R, KEY_L, KEY_X, KEY_Y
    };
    CtrInputSample sample = {0};
    hidScanInput();
    uint32_t raw = hidKeysHeld();
    /* New 3DS: ZR and ZL step the fast-forward speed (OPTIONS has it too),
     * on release; together they open the dev menu, which then has the pad. */
    uint32_t down = hidKeysDown();
    /* the debug driver's words, ZL/ZR among them (bits 12-14 of its own) */
    static uint32_t driveLast;
    uint32_t drive = DriveStep(), driveZ = 0;
    if (drive & (1u << 12)) driveZ |= KEY_ZL;
    if (drive & (1u << 13)) driveZ |= KEY_ZR;
    if (drive & (1u << 14)) driveZ |= KEY_ZL | KEY_ZR;
    {
        static const uint32_t padKeys[12] = {KEY_A, KEY_B, KEY_SELECT, KEY_START, KEY_DRIGHT, KEY_DLEFT,
                                             KEY_DUP, KEY_DDOWN, KEY_R, KEY_L, KEY_X, KEY_Y};
        uint32_t pad = 0;

        for (unsigned i = 0; i < 12; ++i)
            if (drive & (1u << i))
                pad |= padKeys[i];
        down |= (pad | driveZ) & ~driveLast;
        raw |= driveZ;
        driveLast = pad | driveZ;
    }
    bool turboA = false;
    uint32_t menu = CtrDevMenu_Input(raw, down, &turboA);
    for (unsigned i = 0; i < sizeof(keys) / sizeof(keys[0]); ++i)
        if (raw & keys[i])
            sample.buttons |= 1u << i;
    sample.buttons |= drive & 0xFFFu;
    if (turboA)
        sample.buttons |= 1u << 0; /* A */
    if (menu)
        sample.buttons = 0;
    circlePosition circle;
    hidCircleRead(&circle);
    sample.circleX = circle.dx;
    sample.circleY = circle.dy;
    sample.touchActive = (raw & KEY_TOUCH) != 0;
    if (sample.touchActive)
    {
        touchPosition touch;
        hidTouchRead(&touch);
        sample.touchX = touch.px;
        sample.touchY = touch.py;
    }
    CtrInput_Update(&sInput, &sample);
}

const CtrInput *CtrInput_Get(void)
{
    return &sInput;
}
