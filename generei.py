import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ── Palette ────────────────────────────────────────────────────
C = dict(
    ind='#1B3F6E', cond='#5C2480', sp='#145C30',
    si='#7A3B00',  imp='#8B1A1A', bg='#FFFFFF',
    white='#FFFFFF', border='#B0BBCC', text='#111111',
    ind_alt='#E8F0FA', cond_alt='#F3E8FC', sp_alt='#E6F7EE',
    si_alt='#FDF0E0', imp_alt='#FAE8E8',
)

# ── Figure setup ───────────────────────────────────────────────
FW, FH = 15, 15          # inches  (square-ish, scales at print)
DPI = 140
fig = plt.figure(figsize=(FW, FH), dpi=DPI)
fig.patch.set_facecolor(C['bg'])
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

# ── Low-level drawing helpers ──────────────────────────────────
def box(x, y, w, h, fc, ec='none', lw=0, r=0.005, z=2, alpha=1):
    p = FancyBboxPatch((x, y), w, h,
        boxstyle=f'round,pad=0,rounding_size={r}',
        facecolor=fc, edgecolor=ec, linewidth=lw,
        alpha=alpha, zorder=z, transform=ax.transAxes)
    ax.add_patch(p)

def tx(x, y, s, fs=9, c='#111111', bold=False, ha='center', va='center', it=False, z=5):
    ax.text(x, y, s, fontsize=fs, color=c,
            fontweight='bold' if bold else 'normal',
            fontstyle='italic' if it else 'normal',
            ha=ha, va=va, zorder=z, transform=ax.transAxes,
            fontfamily='DejaVu Sans', clip_on=False)

def hline(x0, x1, y, lw=0.5, color=None):
    ax.plot([x0, x1], [y, y], color=color or C['border'],
            lw=lw, transform=ax.transAxes, zorder=6)

def vline(x, y0, y1, lw=0.5, color=None):
    ax.plot([x, x], [y0, y1], color=color or C['border'],
            lw=lw, transform=ax.transAxes, zorder=6)

# ── Section banner ─────────────────────────────────────────────
def sec_banner(x, y, w, h, label, color, fs=11):
    box(x, y, w, h, color, r=0.007, z=3)
    tx(x+w/2, y+h/2, label, fs=fs, c='white', bold=True)

# ── Pill (example sentence) ────────────────────────────────────
def pill(x, y, text, color, fs=7.5):
    ax.text(x, y+0.008, f'  {text}  ', fontsize=fs, color=color,
        ha='left', va='center', transform=ax.transAxes,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFBE6',
                  edgecolor=color, linewidth=1.0),
        fontstyle='italic', zorder=6)

# ── Table drawing ──────────────────────────────────────────────
# col_widths must sum to total width
# returns bottom-y of the drawn table
def table(x0, y_top, col_widths, headers, rows,
          hdr_bg, alt_bg, row_h=0.028, fs=8.5, hfs=8.0, bold_cols=None):
    tw = sum(col_widths)
    n  = len(rows)
    th = row_h * (n + 1)
    yb = y_top - th          # bottom-y

    # background card
    box(x0, yb, tw, th, C['white'], ec=C['border'], lw=0.6, r=0.005, z=2)

    # header row
    box(x0, y_top - row_h, tw, row_h, hdr_bg, r=0.005, z=3)
    cx = x0
    for col, cw in zip(headers, col_widths):
        tx(cx + cw/2, y_top - row_h/2, col, fs=hfs, c='white', bold=True)
        cx += cw

    # data rows
    for ri, row in enumerate(rows):
        ry = y_top - row_h*(ri+2)
        if ri % 2 == 0:
            box(x0, ry, tw, row_h, alt_bg, alpha=0.65, z=2)
        cx = x0
        for ci, (cell, cw) in enumerate(zip(row, col_widths)):
            is_bold_col = bold_cols and ci in bold_cols
            is_pron = (ci == 0)
            tx(cx + cw/2, ry + row_h/2, cell,
               fs=fs, c=hdr_bg if (is_pron or is_bold_col) else C['text'],
               bold=(is_pron or is_bold_col))
            cx += cw

    # grid
    for ri in range(n+2):
        hline(x0, x0+tw, y_top - row_h*ri)
    cx = x0
    for cw in col_widths:
        vline(cx, yb, y_top)
        cx += cw
    vline(cx, yb, y_top)

    return yb

# ══════════════════════════════════════════════════════════════════
# LAYOUT CONSTANTS
# ══════════════════════════════════════════════════════════════════
RH   = 0.028    # row height (normalized)
SH   = 0.033    # section banner height
GAP  = 0.012    # vertical gap
PH   = 0.022    # pill height (space reserved)
LH   = 0.020    # sub-label height
M    = 0.020    # left/right margin
W    = 1 - 2*M  # total content width = 0.96
LW   = 0.455    # left column width
RW   = 0.455    # right column width
LC   = M        # left col start x
RC   = M + LW + 0.03  # right col start x

# ── TITLE ──────────────────────────────────────────────────────
box(M, 0.960, W, 0.035, C['ind'], r=0.008, z=3)
tx(0.5, 0.9775, 'CONJUGAISONS ESPAGNOLES  —  Aide-mémoire', fs=14, c='white', bold=True)

y = 0.955  # current top cursor

# ══════════════════════════════════════════════════════════════════
# 1. INDICATIF  (full width)
# ══════════════════════════════════════════════════════════════════
y -= GAP
sec_banner(M, y-SH, W, SH, 'INDICATIF', C['ind'])
y -= SH + 0.006

cw_i = [0.100, 0.095, 0.125, 0.120, 0.088, 0.138, 0.125, 0.089]
# sum = 0.880, scale to W=0.96
scale = W / sum(cw_i)
cw_i = [c*scale for c in cw_i]

h_i = ['Pronom', 'Plus-que-parf.', 'Imparfait\n-AR / -ER/-IR',
        'Prétérit\n-AR / -ER/-IR', 'Pret.\nperfecto',
        'Présent\n-AR / -ER/-IR', 'Futur\nantérieur', 'Futur\nsimple']
rows_i = [
    ['yo',          'había + PP',    'aba / ía',      'é / í',         'he + PP',   'o / o',          'habré + PP',   'ré'],
    ['tú',          'habías + PP',   'abas / ías',    'aste / iste',   'has + PP',  'as / es',        'habrás + PP',  'rás'],
    ['él/ella/ud.', 'había + PP',    'aba / ía',      'ó / ió',        'ha + PP',   'a / e',          'habrá + PP',   'rá'],
    ['nosotros',    'habíamos+PP',   'ábamos/íamos',  'amos / imos',   'hemos+PP',  'amos/emos/imos', 'habremos+PP',  'remos'],
    ['vosotros',    'habíais + PP',  'abais / íais',  'asteis/isteis', 'habéis+PP', 'áis/éis/ís',     'habréis + PP', 'réis'],
    ['ellos/uds.',  'habían + PP',   'aban / ían',    'aron / ieron',  'han + PP',  'an / en',        'habrán + PP',  'rán'],
]
y = table(M, y, cw_i, h_i, rows_i, C['ind'], C['ind_alt'], row_h=RH, fs=8.0, hfs=8.0)

# Verbes irréguliers — tableau complet (full width, 11 data rows)
y -= GAP
tx(M, y-LH/2, 'Verbes irréguliers essentiels', fs=8.5, c=C['ind'], bold=True, ha='left')
y -= LH

cw_vi = [0.072, 0.165, 0.165, 0.145, 0.160, 0.110]
s = W/sum(cw_vi); cw_vi=[c*s for c in cw_vi]
rows_vi = [
    ['ser',    'soy / eres / es…',      'fui / fuiste / fue…',      'era / eras…',        'ser-',    'sido'],
    ['ir',     'voy / vas / va…',       'fui / fuiste / fue…',      'iba / ibas…',        'ir-',     'ido'],
    ['tener',  'tengo / tienes…',       'tuve / tuviste…',          'tenía / tenías…',    'tendr-',  'tenido'],
    ['venir',  'vengo / vienes…',       'vine / viniste…',          'venía / venías…',    'vendr-',  'venido'],
    ['hacer',  'hago / haces…',         'hice / hiciste…',          'hacía / hacías…',    'har-',    'hecho'],
    ['decir',  'digo / dices…',         'dije / dijiste…',          'decía / decías…',    'dir-',    'dicho'],
    ['poder',  'puedo / puedes…',       'pude / pudiste…',          'podía / podías…',    'podr-',   'podido'],
    ['poner',  'pongo / pones…',        'puse / pusiste…',          'ponía / ponías…',    'pondr-',  'puesto'],
    ['saber',  'sé / sabes…',           'supe / supiste…',          'sabía / sabías…',    'sabr-',   'sabido'],
    ['querer', 'quiero / quieres…',     'quise / quisiste…',        'quería / querías…',  'querr-',  'querido'],
    ['estar',  'estoy / estás…',        'estuve / estuviste…',      'estaba / estabas…',  'estar-',  'estado'],
]
y = table(M, y, cw_vi,
          ['Verbe', 'Présent', 'Prétérit', 'Imparfait', 'Futur / Cond.', 'Part. passé'],
          rows_vi, '#2C5F8A', C['ind_alt'], row_h=RH*0.95, fs=8.0, hfs=8.0)

# ══════════════════════════════════════════════════════════════════
# 2. CONDITIONNEL (left)  |  SUBJONCTIF PRÉSENT (right)
# ══════════════════════════════════════════════════════════════════
y -= GAP * 1.5
y_2col_top = y   # save y for right column

# ── CONDITIONNEL ──────────────────────────────────────────────
sec_banner(LC, y-SH, LW, SH, 'CONDITIONNEL', C['cond'])
y -= SH + 0.006
pill(LC, y-PH, '¿Te gustaría un café?', C['cond'])
y -= PH + 0.006

# 2 sub-tables side by side inside left column
SUB1W = LW*0.42    # terminaisons
SUB2W = LW*0.55    # irréguliers
SUB_GAP = LW - SUB1W - SUB2W

cw_ct = [SUB1W*0.50, SUB1W*0.50]
rows_ct = [['yo','ría'],['tú','rías'],['él/ella/ud.','ría'],
           ['nosotros','ríamos'],['vosotros','ríais'],['ellos/uds.','rían']]
table(LC, y, cw_ct, ['Pronom','Terminaison (tous verbes)'],
      rows_ct, C['cond'], C['cond_alt'], row_h=RH, fs=9, hfs=8.5)

cw_ci = [SUB2W*0.27, SUB2W*0.23, SUB2W*0.27, SUB2W*0.23]
rows_ci = [
    ['tener','tendr-','hacer','har-'],
    ['poder','podr-','poner','pondr-'],
    ['venir','vendr-','decir','dir-'],
    ['saber','sabr-','salir','saldr-'],
    ['haber','habr-','querer','querr-'],
    ['caber','cabr-','—','—'],
]
tx(LC+SUB1W+SUB_GAP, y+LH/2, 'Racines irrégulières', fs=8, c=C['cond'], bold=True, ha='left')
table(LC+SUB1W+SUB_GAP, y-LH*0.3, cw_ci,
      ['Infinitif','Racine','Infinitif','Racine'],
      rows_ci, '#7A3A9A', C['cond_alt'], row_h=RH, fs=8.5, hfs=8.0, bold_cols={0,2})

# ── SUBJONCTIF PRÉSENT ────────────────────────────────────────
y = y_2col_top
sec_banner(RC, y-SH, RW, SH, 'SUBJONCTIF PRÉSENT', C['sp'])
y -= SH + 0.006
pill(RC, y-PH, 'Es importante que comas frutas.', C['sp'], fs=7.2)
pill(RC+0.25, y-PH, 'Es posible que estés enfadado/a.', C['sp'], fs=7.2)
y -= PH + 0.006

# Terminaisons + 2 sets of irregulars side by side
SPA = RW * 0.32   # terminaisons
SPB = RW * 0.33   # irr set 1
SPC = RW * 0.33   # irr set 2
GG  = 0.003

cw_spt = [SPA*0.52, SPA*0.24, SPA*0.24]
rows_spt=[['yo','e','a'],['tú','es','as'],['él/ud.','e','a'],
          ['nosotros','emos','amos'],['vosotros','éis','áis'],['ellos/uds.','en','an']]
table(RC, y, cw_spt, ['Pronom','-AR','-ER/-IR'],
      rows_spt, C['sp'], C['sp_alt'], row_h=RH, fs=9, hfs=8.5)

cw_spi = [SPB*0.48, SPB*0.52]
rows_spi1=[['SER','s-ea'],['IR','v-aya'],['ESTAR','est-é'],
           ['TENER','teng-a'],['HACER','hag-a'],['DECIR','dig-a']]
rows_spi2=[['PODER','pued-a'],['PONER','pong-a'],['VENIR','veng-a'],
           ['DAR','d-é'],['SABER','sep-a'],['SALIR','salg-a']]
table(RC+SPA+GG, y, cw_spi, ['Verbe','yo'],
      rows_spi1, '#2A7A4A', C['sp_alt'], row_h=RH, fs=9, hfs=8.5)
table(RC+SPA+SPB+2*GG, y, [SPC*0.48,SPC*0.52], ['Verbe','yo'],
      rows_spi2, '#2A7A4A', C['sp_alt'], row_h=RH, fs=9, hfs=8.5)

# bottom of this 2-col section (same nb of rows, same row_h)
n_rows_2col = max(len(rows_ct), len(rows_spt))  # = 6
y_after_2col = y_2col_top - SH - PH - LH*0.3 - RH*(n_rows_2col+1) - 0.010

# ══════════════════════════════════════════════════════════════════
# 3. SUBJONCTIF IMPARFAIT (left)  |  IMPÉRATIF (right)
# ══════════════════════════════════════════════════════════════════
y3 = y_after_2col - GAP*1.5
y3_top = y3

# ── SUBJONCTIF IMPARFAIT ──────────────────────────────────────
sec_banner(LC, y3-SH, LW, SH, 'SUBJONCTIF IMPARFAIT', C['si'])
y3 -= SH + 0.006
pill(LC, y3-PH, 'Es posible que estuvieras enfadado/a.', C['si'], fs=7.2)
y3 -= PH + GAP*0.4
pill(LC, y3-PH, 'Si tuvieras dinero, comprarías un coche.  →  si + subj. imp. + cond.', C['si'], fs=7.2)
y3 -= PH + 0.006

SIA = LW * 0.32
SIB = LW * 0.33
SIC = LW * 0.33

cw_sit = [SIA*0.52, SIA*0.24, SIA*0.24]
rows_sit=[['yo','ara','iera'],['tú','aras','ieras'],['él/ud.','ara','iera'],
          ['nosotros','áramos','iéramos'],['vosotros','arais','ierais'],['ellos/uds.','aran','ieran']]
table(LC, y3, cw_sit, ['Pronom','-AR','-ER/-IR'],
      rows_sit, C['si'], C['si_alt'], row_h=RH, fs=9, hfs=8.5)

cw_siirr=[SIB*0.42,SIB*0.58]
rows_siirr1=[['SER/IR','fue-ra'],['ESTAR','estuv-iera'],['TENER','tuv-iera'],
             ['HACER','hic-iera'],['DECIR','dij-era'],['PODER','pud-iera']]
rows_siirr2=[['PONER','pus-iera'],['VENIR','vin-iera'],['HABER','hub-iera'],
             ['QUERER','quis-iera'],['DAR','d-iera'],['IR','fuera']]
table(LC+SIA+GG, y3, cw_siirr, ['Verbe','Racine'],
      rows_siirr1, '#A0520A', C['si_alt'], row_h=RH, fs=9, hfs=8.5)
table(LC+SIA+SIB+2*GG, y3, [SIC*0.42,SIC*0.58], ['Verbe','Racine'],
      rows_siirr2, '#A0520A', C['si_alt'], row_h=RH, fs=9, hfs=8.5)

# ── IMPÉRATIF ─────────────────────────────────────────────────
y4 = y3_top
sec_banner(RC, y4-SH, RW, SH, 'IMPÉRATIF', C['imp'])
y4 -= SH + 0.006

IMA = RW * 0.38
IMB = RW * 0.60

cw_imt=[IMA*0.38, IMA*0.31, IMA*0.31]
rows_imt=[['tú','a','e'],['usted','e','a'],['nosotros','emos','amos'],
          ['vosotros','ad','ed / id'],['ustedes','en','an']]
table(RC, y4, cw_imt, ['Pronom','-AR','-ER/-IR'],
      rows_imt, C['imp'], C['imp_alt'], row_h=RH, fs=9, hfs=8.5)

cw_imi=[IMB*0.20, IMB*0.20, IMB*0.20, IMB*0.20, IMB*0.20]
rows_imi=[
    ['tú',      'sé',    've',     'ten',     'haz'],
    ['usted',   'sea',   'vaya',   'tenga',   'haga'],
    ['nosotros','seamos','vayamos','tengamos','hagamos'],
    ['vosotros','sed',   'id',     'tened',   'haced'],
    ['ustedes', 'sean',  'vayan',  'tengan',  'hagan'],
]
tx(RC+IMA+GG, y4+LH/2, 'Formes irrégulières', fs=8, c=C['imp'], bold=True, ha='left')
table(RC+IMA+GG, y4-LH*0.3, cw_imi,
      ['Pronom','SER','IR','TENER','HACER'],
      rows_imi, '#A02020', C['imp_alt'], row_h=RH, fs=8.5, hfs=8.0)

# ══════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════
# Calculate bottom of all content
y_bottom = y3_top - SH - 2*PH - GAP*0.4 - RH*7 - 0.010
box(M, y_bottom-0.028, W, 0.025, '#2A2A3A', r=0.005, z=3)
tx(0.5, y_bottom-0.016,
   'PP = Participe Passé  •  Futur & Cond. = infinitif + terminaison  •  '
   'Subj. prés. = racine 1ère pers. prés. + terminaison inversée  •  '
   'Subj. imp. = prétérit 3ème pl. → remplacer -aron/-ieron par terminaison',
   fs=6.8, c='#D0CDE0')

plt.savefig('conjugaisons.jpg',
            dpi=DPI, bbox_inches='tight',
            facecolor=C['bg'], format='jpeg',
            pil_kwargs={'quality': 96})
print('Done')
