"""One-off: trace the nine19een logo into two ASCII layers on one grid."""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROWS=int(sys.argv[1]); RATIO=1.9       # line height / char width
CW,CH=12,23                             # glyph cell px for shape matching (ratio ~1.9)
X0,Y0,X1,Y1=20,24,1320,336
lg=Image.open('logo.png').convert('RGB').crop((X0,Y0,X1,Y1))
a=np.asarray(lg).astype(int); r,g,b=a[...,0],a[...,1],a[...,2]
purple=(b>110)&(b-g>45)
grey=(np.abs(r-g)<25)&(np.abs(b-g)<30)&(g>95)
# keep grey only outside the 19's box
grey[:, 500-X0:870-X0]=False          # the 19's column: drop its white highlights
W,H=lg.size
COLS=round(ROWS*RATIO*W/H)
# ---- letters: solid shapes from scattered "19"s
gl=np.asarray(Image.fromarray((grey*255).astype('uint8')).filter(ImageFilter.GaussianBlur(9)),float)
gl=Image.fromarray(((gl>gl.max()*0.18)*255).astype('uint8'))
gl=np.asarray(gl.resize((COLS,ROWS),Image.BOX),float)/255
# ---- the 19: shape-match line characters
font=ImageFont.truetype('ibm-plex-mono-400.ttf',20)
CH_SET=" .,:;'`-_=~^|/\\()[]<>{}!ilLjJTVvYx"
def glyph(c):
    im=Image.new('L',(CW,CH),0); ImageDraw.Draw(im).text((0,1),c,font=font,fill=255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)),float)/255
G={c:glyph(c) for c in CH_SET}
pb=Image.fromarray((purple*255).astype('uint8')).resize((COLS*CW,ROWS*CH),Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
pb=np.clip(np.asarray(pb,float)/255*float(sys.argv[2]),0,1)
L19,LET=[],[]
thr=float(sys.argv[3])
for y in range(ROWS):
    s=t=''
    for x in range(COLS):
        p=pb[y*CH:(y+1)*CH,x*CW:(x+1)*CW]
        s+=' ' if p.mean()<0.02 else min(CH_SET,key=lambda ch:((G[ch]-p)**2).sum())
        t+=('1' if x%2==0 else '9') if gl[y,x]>thr else ' '
    L19.append(s.rstrip()); LET.append(t.rstrip())
open('banner-19.txt','w').write('\n'.join(L19)+'\n'); open('banner-letters.txt','w').write('\n'.join(LET)+'\n')
for s,t in zip(L19,LET):
    print(''.join(a if a!=' ' else b for a,b in zip(s.ljust(COLS),t.ljust(COLS))).rstrip())
print(ROWS,COLS)
