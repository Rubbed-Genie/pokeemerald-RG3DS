/*
 * RG3DS dev menu: ZL and ZR pressed together drop a panel down from the top
 * of the top screen. Up and down pick a row, ZL/ZR (or left/right) change it,
 * B or ZL+ZR again put it away. While it is down the game gets no buttons.
 * ZL or ZR alone still steps the fast-forward speed, on release, so the chord
 * never steps it on the way.
 *
 * Its own 5x7 pixel font, drawn as solid rectangles like the FPS counter: the
 * console's system font is not there under every emulator.
 */
#include <3ds.h>
#include <citro2d.h>
#include <stdio.h>
#include <string.h>

#include "3ds_platform.h"
#include "3ds_devmenu.h"

/* Their clock (3ds_daynight.c) holds settings dev_hour; the town warp is the
 * game bridge's (3ds_game_full.c). */
void CtrGame_WarpToTown(int town);

/* ── Font ──────────────────────────────────────────────────────────────── */

static const char sChars[] = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ:-+./%<>";
static const uint8_t sGlyphs[][7] =
{
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, /* space */
    {0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E}, /* 0 */
    {0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E}, /* 1 */
    {0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F}, /* 2 */
    {0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E}, /* 3 */
    {0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02}, /* 4 */
    {0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E}, /* 5 */
    {0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E}, /* 6 */
    {0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08}, /* 7 */
    {0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E}, /* 8 */
    {0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C}, /* 9 */
    {0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11}, /* A */
    {0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E}, /* B */
    {0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E}, /* C */
    {0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C}, /* D */
    {0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F}, /* E */
    {0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10}, /* F */
    {0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F}, /* G */
    {0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11}, /* H */
    {0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E}, /* I */
    {0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C}, /* J */
    {0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11}, /* K */
    {0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F}, /* L */
    {0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11}, /* M */
    {0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11}, /* N */
    {0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E}, /* O */
    {0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10}, /* P */
    {0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D}, /* Q */
    {0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11}, /* R */
    {0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E}, /* S */
    {0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04}, /* T */
    {0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E}, /* U */
    {0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04}, /* V */
    {0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A}, /* W */
    {0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11}, /* X */
    {0x11, 0x11, 0x11, 0x0A, 0x04, 0x04, 0x04}, /* Y */
    {0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F}, /* Z */
    {0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00}, /* : */
    {0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00}, /* - */
    {0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00}, /* + */
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C}, /* . */
    {0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10}, /* / */
    {0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03}, /* % */
    {0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02}, /* < */
    {0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08}, /* > */
};

#define PIXEL 1.0f
#define ADVANCE (6.0f * PIXEL)
#define LINE (11.0f * PIXEL)

static void DrawText(const char *text, float x, float y, u32 colour)
{
    for (; *text; ++text, x += ADVANCE)
    {
        char c = *text >= 'a' && *text <= 'z' ? (char)(*text - 32) : *text;
        const char *at = strchr(sChars, c);
        const uint8_t *g;

        if (at == NULL || c == 0)
            continue;
        g = sGlyphs[at - sChars];
        for (int row = 0; row < 7; ++row)
            for (int col = 0; col < 5; ++col)
                if (g[row] & (0x10 >> col))
                    C2D_DrawRectSolid(x + col * PIXEL, y + row * PIXEL, 0, PIXEL, PIXEL, colour);
    }
}

/* ── Rows ──────────────────────────────────────────────────────────────── */

enum { ROW_TIME, ROW_DAYNIGHT, ROW_NIGHTDARK, ROW_WEATHER, ROW_WARP, ROW_ZLZR, ROW_COUNT };

/* What L2/R2 do on their own (zlzr_mode): step the speed, hold for turbo A,
 * or cycle the time of day or the weather. */
enum { ZLZR_SPEED, ZLZR_TURBO, ZLZR_TIME, ZLZR_WEATHER, ZLZR_MODES };
static const char *const sZlzrNames[] = {"SPEED", "TURBO A", "TIME OF DAY", "WEATHER"};

/* The game's weather (3ds_game_full.c): its name, and a step through them. */
const char *CtrGame_WeatherName(void);
void CtrGame_StepWeather(int direction);

static int ZlzrMode(void)
{
    int mode = CtrSettings_GetInt("zlzr_mode", -1);

    if (mode < 0)
        mode = ZLZR_TURBO;   /* the default */
    return mode >= 0 && mode < ZLZR_MODES ? mode : ZLZR_SPEED;
}

/* The hours sit on the clock's keys (3ds_daynight.c): morning light 4-8,
 * full day 10-15, evening 17-18, night from 20. */
static const char *const sTimeNames[] = {"REAL CLOCK", "MORNING", "DAY", "EVENING", "NIGHT"};
static const int sTimeHours[] = {-1, 7, 12, 18, 22};

static int TimeIndex(void)
{
    int hour = CtrSettings_GetInt("dev_hour", -1);

    for (int i = 0; i < (int)(sizeof(sTimeHours) / sizeof(sTimeHours[0])); ++i)
        if (sTimeHours[i] == hour)
            return i;
    return 0;
}

static const char *const sTowns[] = {"SLATEPORT", "RUSTBORO", "DEWFORD", "PETALBURG", "MAUVILLE"};
#define TOWNS 5
static int sTown;

static void RowText(int row, char *label, char *value, size_t size)
{
    switch (row)
    {
    case ROW_TIME:
        strcpy(label, "TIME OF DAY");
        snprintf(value, size, "%s", sTimeNames[TimeIndex()]);
        break;
    case ROW_DAYNIGHT:
        strcpy(label, "DAY/NIGHT");
        snprintf(value, size, "%s", CtrSettings_GetInt("day_night", 0) == 1 ? "ON" : "OFF");
        break;
    case ROW_NIGHTDARK:
        /* the light kept at full night (3ds_daynight.c) */
        strcpy(label, "NIGHT LIGHT");
        snprintf(value, size, "%d%%", CtrSettings_GetInt("night_dark", 45));
        break;
    case ROW_WEATHER:
        strcpy(label, "WEATHER");
        snprintf(value, size, "%s", CtrGame_WeatherName());
        break;
    case ROW_WARP:
        strcpy(label, "WARP A:GO");
        snprintf(value, size, "<%s>", sTowns[sTown]);
        break;
    default:
        strcpy(label, "L2/R2 DOES");
        snprintf(value, size, "%s", sZlzrNames[ZlzrMode()]);
        break;
    }
}

static void ChangeRow(int row, int direction)
{
    switch (row)
    {
    case ROW_TIME:
    {
        int count = (int)(sizeof(sTimeHours) / sizeof(sTimeHours[0]));
        int next = (TimeIndex() + direction + count) % count;

        CtrSettings_SetInt("dev_hour", sTimeHours[next]);
        /* a held hour means nothing with their day/night off */
        if (sTimeHours[next] >= 0)
            CtrSettings_SetInt("day_night", 1);
        break;
    }
    case ROW_DAYNIGHT:
        CtrSettings_SetInt("day_night", CtrSettings_GetInt("day_night", 0) == 1 ? 0 : 1);
        break;
    case ROW_NIGHTDARK:
    {
        int v = CtrSettings_GetInt("night_dark", 45) + direction * 5;

        CtrSettings_SetInt("night_dark", v < 10 ? 10 : v > 100 ? 100 : v);
        break;
    }
    case ROW_WEATHER:
        CtrGame_StepWeather(direction);
        break;
    case ROW_WARP:
        sTown = (sTown + direction + TOWNS) % TOWNS;
        break;
    default:
        CtrSettings_SetInt("zlzr_mode", (ZlzrMode() + direction + ZLZR_MODES) % ZLZR_MODES);
        break;
    }
}

/* ── State and input ───────────────────────────────────────────────────── */

static bool sOpen;
static int sRow;
static float sDrop;      /* 0 hidden .. 1 fully down */
static int sChord;       /* frames since the first of ZL/ZR went down, 0 none */
static bool sChordUsed;  /* both went down: no speed step on release */
static uint32_t sLast;   /* last frame's held ZL/ZR */
static bool sTurbo;      /* this hold was turbo A: no speed step on release */

bool CtrDevMenu_Open(void)
{
    return sOpen;
}

/* Frames ZL/ZR alone must be held before turbo A starts: time for the
 * other to join it (the menu's chord). */
#define TURBO_DELAY 8
/* A pressed this many frames of every TURBO_PERIOD while held. */
#define TURBO_PERIOD 6

/* held/down: hidKeysHeld/hidKeysDown. Returns the game buttons to clear;
 * *pressA set when the game should see A this frame (turbo). */
uint32_t CtrDevMenu_Input(uint32_t held, uint32_t down, bool *pressA)
{
    uint32_t z = held & (KEY_ZL | KEY_ZR);
    uint32_t released = sLast & ~z;

    if ((down & (KEY_ZL | KEY_ZR)) && sChord == 0)
    {
        sChord = 1;
        sChordUsed = false;
    }
    if (z == (KEY_ZL | KEY_ZR) && !sChordUsed)
    {
        sChordUsed = true;
        sOpen = !sOpen;
    }
    /* RG3DS: one of them alone does what the L2/R2 row says - open or not,
     * the menu is the D-pad's */
    else if (!sChordUsed && released && z == 0 && !sTurbo)
    {
        if (ZlzrMode() == ZLZR_SPEED)
            CtrSettings_StepSpeed((released & KEY_ZR) ? 1 : -1, false);
        else if (ZlzrMode() == ZLZR_TIME)
            ChangeRow(ROW_TIME, (released & KEY_ZR) ? 1 : -1);
        else if (ZlzrMode() == ZLZR_WEATHER)
            CtrGame_StepWeather((released & KEY_ZR) ? 1 : -1);
    }
    *pressA = false;
    if (!sOpen && !sChordUsed && z != 0 && z != (KEY_ZL | KEY_ZR) && sChord > TURBO_DELAY
     && ZlzrMode() == ZLZR_TURBO)
    {
        sTurbo = true;
        *pressA = ((sChord - TURBO_DELAY) % TURBO_PERIOD) < TURBO_PERIOD / 2;
    }
    if (z == 0 && !released)
        sTurbo = false;
    if (z == 0)
        sChord = 0;
    else if (sChord)
        ++sChord;
    sLast = z;

    if (!sOpen)
        return 0;
    if (down & KEY_B)
        sOpen = false;
    if (down & KEY_DUP)
        sRow = (sRow + ROW_COUNT - 1) % ROW_COUNT;
    if (down & KEY_DDOWN)
        sRow = (sRow + 1) % ROW_COUNT;
    if (down & KEY_DLEFT)
        ChangeRow(sRow, -1);
    if ((down & KEY_A) && sRow == ROW_WARP)
    {
        /* the warp waits for the menu to close (3ds_game_full.c) */
        CtrGame_WarpToTown(sTown);
        sOpen = false;
    }
    else if (down & (KEY_DRIGHT | KEY_A))
        ChangeRow(sRow, 1);
    return ~0u;
}

/* ── Drawing ───────────────────────────────────────────────────────────── */

void CtrDevMenu_Draw(C3D_RenderTarget *target)
{
    float height = 18.0f + ROW_COUNT * LINE + 14.0f, top;
    float left = (400.0f - 200.0f) * 0.5f; /* the top target is 400 wide */

    sDrop += sOpen ? 0.2f : -0.2f;
    if (sDrop < 0.0f) sDrop = 0.0f;
    if (sDrop > 1.0f) sDrop = 1.0f;
    if (sDrop <= 0.0f)
        return;
    top = -height + height * (1.0f - (1.0f - sDrop) * (1.0f - sDrop));

    C2D_Prepare();
    C3D_DepthTest(false, GPU_ALWAYS, GPU_WRITE_COLOR);
    C2D_SceneBegin(target);
    C2D_ViewReset();
    C2D_DrawRectSolid(left, top, 0, 200.0f, height, C2D_Color32(16, 20, 36, 225));
    C2D_DrawRectSolid(left, top + height - 2.0f, 0, 200.0f, 2.0f, C2D_Color32(120, 200, 255, 255));
    DrawText("RG3DS DEV MENU", left + 8.0f, top + 6.0f, C2D_Color32(120, 200, 255, 255));
    for (int row = 0; row < ROW_COUNT; ++row)
    {
        char label[24], value[24];
        float y = top + 18.0f + row * LINE;
        u32 colour = row == sRow ? C2D_Color32(255, 230, 120, 255) : C2D_Color32(230, 230, 230, 255);

        RowText(row, label, value, sizeof(value));
        if (row == sRow)
            C2D_DrawRectSolid(left + 3.0f, y - 2.0f, 0, 194.0f, LINE - 1.0f, C2D_Color32(60, 70, 110, 255));
        DrawText(label, left + 8.0f, y, colour);
        DrawText(value, left + 192.0f - strlen(value) * ADVANCE, y, colour);
    }
    DrawText("DPAD CHANGE  B CLOSE", left + 8.0f, top + height - 12.0f, C2D_Color32(150, 150, 170, 255));
    C2D_Flush();
}
