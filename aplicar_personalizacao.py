#!/usr/bin/env python3
"""Personalizacao FunTuna Fork SD Ceara Games.

Aplica mudancas somente em um clone do repositorio oficial.
Nao incorpora o codigo original no kit nem modifica a instalacao do PS2.
"""
from pathlib import Path
import hashlib, json, re, shutil, sys

BASE=Path(__file__).resolve().parents[1]
WORK=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else BASE
INSTALLER=WORK/'installer'
PAYLOAD=BASE/'sdceara'

required=[INSTALLER/'main.c',INSTALLER/'Makefile',INSTALLER/'INSTALLER_CONTENTS'/'BOOT'/'FUNTUNA.CNF',INSTALLER/'INSTALLER_CONTENTS'/'APPS'/'OPNPS2LD.ELF']
for p in required:
    if not p.is_file():
        raise SystemExit(f'ERRO: repositorio incompleto ou diretorio incorreto: {p}')

out_elf=INSTALLER/'INSTALLER_CONTENTS'/'APPS'/'OPNPS2LD.ELF'
new_elf=PAYLOAD/'OPL-SD-CEARA-GAMES-XMB-v1.0.ELF'
if new_elf.read_bytes()[:4] != b'\x7fELF':
    raise SystemExit('ELF v1.0 invalido')
# Safety: preserve a backup in this runner only, never overwrite user's card.
backup=WORK/'sdceara-backup-aplicacao'
backup.mkdir(exist_ok=True)
for p in required:
    q=backup/p.relative_to(WORK);q.parent.mkdir(parents=True,exist_ok=True)
    if not q.exists():shutil.copy2(p,q)
shutil.copy2(new_elf,out_elf)

# Replace original huge raw header art with six compact branded bitmap screens.
main_path=INSTALLER/'main.c'
s=main_path.read_text(encoding='latin-1')
includes=r'^#include "(?:FUNTUNA_FORK_INSTALLER_(?:BG|WELCOME|SUCESS|FAIL)|ERROR_MESSAGES/[A-Z0-9_]+)\.h"\s*$'
s,n=re.subn(includes,'',s,flags=re.M)
if n<12:raise SystemExit(f'No suitable upstream bitmap include set (found {n})')
extern='''/* SD CEARA GAMES: images generated from original commissioned artwork. */
extern u32 SD_WELCOME[], SD_CONFIRM[], SD_ICON[], SD_WORKING[], SD_SUCCESS[], SD_ERROR[];
'''
anchor='static int pad_inited = 0;'
if s.count(anchor)!=1:raise SystemExit('Unexpected upstream main.c layout')
s=s.replace(anchor, extern+'\n'+anchor)
error_names={'_NO_MEMORY_CARD','NO_PS2_MC','_NOT_ENOUGH_SPACE','FOUND_FORTUNA','FOUND_OPENTUNA','FOUND_FUNTUNA','FOUND_BOOT','FOUND_APPS','FAIL'}
image_mapping={'BG':'SD_WORKING','WELCOME':'SD_WELCOME','SUCESS':'SD_SUCCESS',
               'INSTALL_QUERY':'SD_CONFIRM','ICONQUERY':'SD_ICON',
               'ICONQUERY_SLIMS':'SD_ICON','ICONQUERY_FATS':'SD_ICON','ICONQUERY_FAT170':'SD_ICON'}
image_mapping.update({n:'SD_ERROR' for n in error_names})
seen=set()
def repl_image(match):
    name=match.group(1)
    if name not in image_mapping:
        raise SystemExit(f'Unknown upstream bitmap screen: {name}')
    seen.add(name)
    return f'display_bmp(640, 448, {image_mapping[name]})'
s,n=re.subn(r'display_bmp\(640,\s*448,\s*([A-Za-z0-9_]+)\)',repl_image,s)
if len(seen)<12: raise SystemExit(f'Incomplete bitmap replacement: {sorted(seen)}')

# Prior installer cleans user BOOT/APPS/OPL folders before checking available space.
# This fork refuses any existing installation, guaranteeing it is only used on a spare/blank card.
marker='if (mc_Type != 2){return NO_PS2_MEMORY_CARD;}'
if s.count(marker)!=1:raise SystemExit('Safety preflight anchor not found')
preflight='''if (mc_Type != 2){return NO_PS2_MEMORY_CARD;}

    /* SD CEARA GAMES SAFETY: never erase BOOT/APPS/OPL on an existing card. */
    if (mc_Free < 3500) return NOT_ENOUGH_SPACE;
    {
        const char *existing[] = {"BOOT", "APPS", "OPL", "BXEXEC-OPENTUNA",
                                  "BXEXEC-FUNTUNA", "FORTUNA", "OPENTUNA"};
        int index;
        for (index=0; index<(int)(sizeof(existing)/sizeof(existing[0])); index++) {
            char target[64];
            DIR *probe;
            snprintf(target, sizeof(target), "mc%u:/%s", mcport, existing[index]);
            probe = opendir(target);
            if (probe != NULL) {
                closedir(probe);
                return index == 1 ? APPS_FOLDER_EXISTS : BOOT_FOLDER_EXISTS;
            }
        }
    }
'''
s=s.replace(marker,preflight)
if s.count('if (mc_Free < 2000)')!=1:raise SystemExit('Expected original capacity guard not found')
s=s.replace('if (mc_Free < 2000)','if (mc_Free < 3500)')
# Portuguese status text (log does not change controls).
s=s.replace('Installing for memory card %u...', 'Instalando no Memory Card %u...')
s=s.replace('Creating Folders...', 'Criando pastas...')
s=s.replace('Writing Files', 'Gravando arquivos')
s=s.replace('Installation Finished','Instalacao concluida')
s=s.replace('No OPL settings found!', 'Sem configuracao OPL anterior!')
s=s.replace('Loading Preconfigured OPL Folder...', 'Preparando ajustes do OPL...')
main_path.write_text(s,encoding='latin-1')

# Prefer installed OPL instead of a possibly outdated USB copy.
cnf_path=INSTALLER/'INSTALLER_CONTENTS'/'BOOT'/'FUNTUNA.CNF'
cnf=cnf_path.read_text(encoding='latin-1')
def set_key(k,v):
    global cnf
    pat=r'(?m)^'+re.escape(k)+r'\s*=.*$'
    cnf,n=re.subn(pat,lambda m:f'{k} = {v}',cnf)
    if n!=1: raise SystemExit(f'Config entry not found or repeated: {k}')
set_key('OSDSYS_selected_color','0x1A,0xD0,0x66,0x80')
set_key('OSDSYS_unselected_color','0xD9,0xDC,0xD4,0x80')
set_key('name_OSDSYS_ITEM_3','SD CEARA GAMES XMB')
set_key('LK_Circle_E1','mc?:/APPS/OPNPS2LD.ELF')
set_key('LK_Circle_E2','mass:/FUNTUNA/OPNPS2LD.ELF')
set_key('LK_Circle_E3','mc?:/OPL/OPNPS2LD.ELF')
set_key('path1_OSDSYS_ITEM_3','mc?:/APPS/OPNPS2LD.ELF')
set_key('path2_OSDSYS_ITEM_3','mass:/FUNTUNA/OPNPS2LD.ELF')
set_key('path3_OSDSYS_ITEM_3','mc?:/OPL/OPNPS2LD.ELF')
cnf=cnf.replace('FunTuna              ','SD CEARA GAMES       ').replace('Based on FreeMcBoot 1.8','Base: FreeMcBoot 1.8 / FunTuna Fork')
cnf_path.write_text(cnf,encoding='latin-1')

for filename in ('conf_opl.cfg','conf_opl1.cfg'):
    cp=INSTALLER/'INSTALLER_CONTENTS'/'OPL'/filename
    conf=cp.read_text(encoding='latin-1')
    for key,value in [('bg_color','#09180E'),('text_color','#F4F8F1'),('ui_text_color','#C7D7CC'),('sel_text_color','#20DF66')]:
        conf,count=re.subn(r'(?m)^'+key+r'=.*$',f'{key}={value}',conf)
        if count!=1:raise SystemExit(f'Invalid OPL config key: {key}')
    cp.write_text(conf,encoding='latin-1')

# Bitmap assembly resources. Original UI images remain in upstream, but are no longer
# included in main.c to avoid bloating the executable.
assetdest=INSTALLER/'SDCEARA'
assetdest.mkdir(exist_ok=True)
res=['SD_WELCOME','SD_CONFIRM','SD_ICON','SD_WORKING','SD_SUCCESS','SD_ERROR']
for name in res:
    raw=PAYLOAD/'ASSETS'/(name+'.rgba')
    if raw.stat().st_size!=640*448*4:raise SystemExit(f'Invalid RGBA asset: {name}')
    shutil.copy2(raw,assetdest/(name+'.rgba'))
makefile=INSTALLER/'Makefile'; mk=makefile.read_text()
if 'SD_WELCOME.o' not in mk:
    lines='\n# SD CEARA GAMES - native installer screens\n'
    lines+='EE_OBJS += '+' '.join(x.lower()+'.o' for x in res)+'\n'
    lines+='EE_SRC += '+' '.join(x.lower()+'.s' for x in res)+'\n'
    lines+='\n'
    for name in res:
        lines+=f'{name.lower()}.s: SDCEARA/{name}.rgba\n\t@bin2s $< $@ {name}\n\n'
    # Append before include to avoid placing rules after default target ambiguity.
    anchor='include $(PS2SDK)/samples/Makefile.pref'
    if mk.count(anchor)!=1:raise SystemExit('Missing PS2SDK Makefile anchor')
    mk=mk.replace(anchor,lines+'\n'+anchor)
makefile.write_text(mk)

report={'project':'SD CEARA GAMES - FunTuna Fork installer','opl_sha256':hashlib.sha256(out_elf.read_bytes()).hexdigest(),
        'art_screens':res, 'safety':'never erase BOOT/APPS/OPL from an already configured memory card',
        'original_credits':'FunTuna Fork and FreeMcBoot credits preserved',
        'github_source':'https://github.com/israpps/Funtuna-Fork','bin_filename':'FunTuna-Fork_Installer.ELF'}
(WORK/'sdceara-build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SD CEARA GAMES - source patch applied successfully')
print('OPL SHA256:',report['opl_sha256'])
print('Modified executable source, boot menu and installer graphics; PS2 build still required.')
