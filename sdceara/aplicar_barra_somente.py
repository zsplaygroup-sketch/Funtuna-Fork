#!/usr/bin/env python3
"""Aplica apenas barra de progresso ao instalador V1; nao modifica FreeMcBoot."""
from pathlib import Path
import re,sys
repo=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
p=repo/'installer/main.c'
s=p.read_text(encoding='latin-1')
a=s.index('static int install(int mcport, int icon_variant)')
b=s.index('static void CleanUp(void)',a)
block=s[a:b]
assert 'SD CEARA GAMES SAFETY' in block, 'Protecao V1 ausente'
assert 'display_bmp(640, 448, SD_WORKING);' in block, 'Tela V1 ausente'
block,n=re.subn(r'\bscr_printf\s*\([^;]*\)\s*;', '', block, flags=re.S)
assert n>=12, f'Esperados prints da V1, encontrados {n}'
def replace(old,new):
 global block
 assert block.count(old)==1, f'Ancora inesperada: {old[:60]}'
 block=block.replace(old,new,1)
replace('display_bmp(640, 448, SD_WORKING);','display_bmp(640, 448, SD_WORKING);\n\tsdProgressUpdate(0);')
for anchor,percent in [('// /CLEANUP',8),('///FOLDERS',25),('///OPENTUNA',45),('///FUNTUNA&APPS',78)]:
 replace(anchor,anchor+f'\n\tsdProgressUpdate({percent});')
replace('if (retorno < 0) {return 6;}\n\tif (!file_exists(opl_settings_location))','if (retorno < 0) {return 6;}\n\tsdProgressUpdate(90);\n\tif (!file_exists(opl_settings_location))')
replace('return 0;\n}\n//--------------------------------------------------------------','sdProgressUpdate(100);\n\treturn 0;\n}\n//--------------------------------------------------------------')
fn='''/* Barra experimental SD Ceara: marcos de etapas reais. */
static void sdProgressUpdate(unsigned int percent)
{
    unsigned int fill;
    if (percent > 100) percent = 100;
    fill = (350 * percent) / 100;
    gs_set_fill_color(27, 127, 74);
    gs_fill_rect(192, 278, 552, 311);
    gs_set_fill_color(218, 174, 51);
    gs_fill_rect(194, 280, 550, 309);
    gs_set_fill_color(5, 26, 17);
    gs_fill_rect(196, 282, 548, 307);
    if (fill > 0) {
        gs_set_fill_color(16, 222, 99);
        gs_fill_rect(197, 283, 197 + fill, 306);
    }
}

'''
s=s[:a]+fn+block+s[b:]
p.write_text(s,encoding='latin-1')
print('Barra aplicada; FreeMcBoot intacto; prints removidos:',n)
