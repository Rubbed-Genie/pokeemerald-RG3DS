#ifndef CTR_DEVMENU_H
#define CTR_DEVMENU_H

#include <stdbool.h>
#include <stdint.h>
#include <citro3d.h>

/* RG3DS dev menu (3ds_devmenu.c): ZL+ZR on the top screen. */
bool CtrDevMenu_Open(void);
/* Each frame from the input scan; while open it returns ~0 (the game's
 * buttons are its own). Steps the speed for a lone ZL/ZR otherwise, or
 * holds it as turbo A (*pressA). */
uint32_t CtrDevMenu_Input(uint32_t held, uint32_t down, bool *pressA);
void CtrDevMenu_Draw(C3D_RenderTarget *target);

#endif
