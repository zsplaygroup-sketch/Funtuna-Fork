#!/usr/bin/env python3
"""FunTuna SD Ceara Games V2 - change ONLY FreeMcBoot splash and installer progress.

Runs AFTER sdceara/aplicar_personalizacao.py from the already tested V1.
Fails closed on unexpected upstream source changes. Does not write to Memory Card.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import zlib

repo=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
asset=repo/'sdceara'/'v2'
installer=repo/'installer'
free=repo/'FreeMcBoot'
assert (repo/'sdceara'/'aplicar_personalizacao.py').is_file(), 'V1 script missing'
assert (installer/'main.c').is_file(), 'FunTuna main.c missing'
assert (free/'splash.h').is_file(), 'FreeMcBoot/splash.h missing'
assert (installer/'SDCEARA'/'SD_WORKING.rgba').is_file(), 'V1 must run first'
assert (installer/'INSTALLER_CONTENTS'/'APPS'/'OPNPS2LD.ELF').is_file(), 'OPL missing'
assert (asset/'SD_WORKING_V2.rgba.zlib').is_file(), 'Compressed progress screen missing'

# 1) The loader's real splash is in FreeMcBoot/splash.h, NOT installer graphics.
raw=zlib.decompress((asset/'SD_BOOT_SPLASH.rgbx.zlib').read_bytes())
w,h=480,168
if len(raw)!=w*h*4:
    raise RuntimeError('Bad splash geometry; refuse to change FreeMcBoot')
# Keep source format and conventional 32-bit pixel values used in original splash.h.
px=[int.from_bytes(raw[i:i+4],'little') for i in range(0,len(raw),4)]
header=['/* SD Ceara Games startup logo; based on approved project artwork. */',
        '#include "defines.h"',f'uint32 splash_w = {w};',f'uint32 splash_h = {h};',
        'uint32 __attribute__((aligned(16))) splash[] = {']
for i in range(0,len(px),10):
    header.append('  '+', '.join(f'0x{x:08x}' for x in px[i:i+10])+',')
header+=['};','']
(free/'splash.h').write_text('\n'.join(header),encoding='ascii')
# The original FreeMcBoot Makefile points to a Windows-only packer executable.
# Use PS2DEV Linux packer already used by the working V1 installer.
fm=free/'Makefile'
mk=fm.read_text(encoding='latin-1')
old='../tools/ps2_packer/ps2_packer.exe -v $< $@'
if mk.count(old)!=1:
    raise RuntimeError('FreeMcBoot packer path changed; cannot patch build safely')
mk=mk.replace(old, 'ps2-packer $< $@')
fm.write_text(mk,encoding='latin-1')

# 2) Eliminate scrolling debug text ONLY during installer install() procedure.
# Keep user-visible welcome, questions, finished and error screens from V1 unchanged.
mainpath=installer/'main.c'
s=mainpath.read_text(encoding='latin-1')
begin='static int install(int mcport, int icon_variant)'
end='static void CleanUp(void)'
if s.count(begin)!=1 or s.count(end)!=1:
    raise RuntimeError('FunTuna install() anchors changed')
a=s.index(begin); b=s.index(end,a)
block=s[a:b]
if 'display_bmp(640, 448, SD_WORKING);' not in block or 'Installation Finished' in block:
    # V1 translates the original message to Portuguese.
    if 'display_bmp(640, 448, SD_WORKING);' not in block:
        raise RuntimeError('V1 working screen missing: run V1 before V2')
# remove only the print statements in installer, not load or error code.
block,removed=re.subn(r'\bscr_printf\s*\([^;]*\)\s*;', '', block, flags=re.S)
if removed<12:
    raise RuntimeError(f'Expected V1 install() progress prints; found {removed}; abort')

# Progress updates are coarse, but represent stages successfully reached,
# not an artificial timer. Every stage after the initial one follows disk writes.
def replace_once(needle, replacement, desc):
    global block
    n=block.count(needle)
    if n!=1:
        raise RuntimeError(f'{desc}: expected exactly one anchor, found {n}')
    block=block.replace(needle,replacement,1)

replace_once('display_bmp(640, 448, SD_WORKING);',
             'display_bmp(640, 448, SD_WORKING);\n\tsdProgressUpdate(0);',
             'initial screen')
# Ensure safety preflight remains intact before write operations.
if 'SD CEARA GAMES SAFETY' not in block:
    raise RuntimeError('V1 memory-card safety preflight missing')
replace_once('// /CLEANUP', '// /CLEANUP\n\tsdProgressUpdate(8);', 'preflight')
replace_once('///FOLDERS', '///FOLDERS\n\tsdProgressUpdate(25);', 'folders')
replace_once('///OPENTUNA', '///OPENTUNA\n\tsdProgressUpdate(45);', 'entrypoint')
replace_once('///FUNTUNA&APPS', '///FUNTUNA&APPS\n\tsdProgressUpdate(78);', 'boot files')
# Stop at OPL launch file: only advance after the embedded v1 ELF was written.
needle='if (retorno < 0) {return 6;}\n\tif (!file_exists(opl_settings_location))'
replace_once(needle,
             'if (retorno < 0) {return 6;}\n\tsdProgressUpdate(90);\n\tif (!file_exists(opl_settings_location))',
             'OPL installed')
# Last status comes at successful return only.
replace_once('return 0;\n}\n//--------------------------------------------------------------',
             'sdProgressUpdate(100);\n\treturn 0;\n}\n//--------------------------------------------------------------', 'completion')

function='''/* SD CEARA GAMES V2: progress without scrolling console text.
 * Values are stage milestones after successful operations, not elapsed time. */
static void sdProgressUpdate(unsigned int percent)
{
    unsigned int fill;
    if (percent > 100) percent = 100;
    fill = (352 * percent) / 100;
    gs_set_fill_color(27, 127, 74);
    gs_fill_rect(192, 278, 552, 311);
    gs_set_fill_color(218, 174, 51);
    gs_fill_rect(194, 280, 550, 309);
    gs_set_fill_color(5, 26, 17);
    gs_fill_rect(196, 282, 548, 307);
    if (fill > 0) {
        gs_set_fill_color(16, 222, 99);
        gs_fill_rect(197, 283, 197 + fill, 306);
        gs_set_fill_color(234, 203, 85);
        gs_fill_rect(197 + fill, 283, 197 + fill, 306);
    }
}

'''
s=s[:a]+function+block+s[b:]
mainpath.write_text(s,encoding='latin-1')
progress_pixels=zlib.decompress((asset/'SD_WORKING_V2.rgba.zlib').read_bytes())
if len(progress_pixels)!=640*448*4:
    raise RuntimeError('Corrupt V2 progress screen')
(installer/'SDCEARA'/'SD_WORKING.rgba').write_bytes(progress_pixels)

report_path=repo/'sdceara-build-report.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
report['version']='2.0'
report['FreeMcBoot_splash']='FreeMcBoot/splash.h generated (480x168): rebuilt BOOT.ELF REQUIRED'
report['installer_progress']='GS green/gold stage progress; install() console scrolling disabled'
report['branding_safe_area']='NTSC 640x448 / PAL 640x512 centered logo'
report['OPL_preserved_sha256']=hashlib.sha256((installer/'INSTALLER_CONTENTS'/'APPS'/'OPNPS2LD.ELF').read_bytes()).hexdigest()
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SD CEARA GAMES V2 source patch OK: FreeMcBoot splash and installer milestone bar')
print('Progress log statements removed only inside install():', removed)
print('OPL kept:', report['OPL_preserved_sha256'])
print('Rebuilding FreeMcBoot from source is REQUIRED; do not substitute the V1 BOOT.ELF')
