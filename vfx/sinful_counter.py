# Oathbreaker - Sinful Counter: dark sword-slash VFX, 4 dirs (S,N,W,E) x 6 frames, 48x48
import math, random
from PIL import Image
S=48; C=24
DARK=(26,8,36,255); PRIM=(91,26,138,255); SEC=(176,32,58,255); ACC=(255,90,122,255); HOT=(255,214,232,255)
# (inner r, outer r, arc start, arc end deg, sparks, alpha-dither)
FR=[None,
    dict(ri=6, ro=9, a0=-70,a1=-40,sp=6, dith=0),
    dict(ri=9, ro=14,a0=-75,a1=-5, sp=4, dith=0),
    dict(ri=10,ro=18,a0=-80,a1=45, sp=4, dith=0),
    dict(ri=9, ro=21,a0=-90,a1=90, sp=8, dith=0),   # impact, strongest
    dict(ri=14,ro=20,a0=-40,a1=95, sp=12,dith=1),
    dict(ri=17,ro=20,a0=40, a1=95, sp=8, dith=2)]
def frame(f,base):
    im=Image.new("RGBA",(S,S),(0,0,0,0)); px=im.load(); p=FR[f]; rnd=random.Random(f*7+base)
    span=p['a1']-p['a0']
    for y in range(S):
        for x in range(S):
            dx,dy=x+.5-C,y+.5-C; r=math.hypot(dx,dy)
            a=(math.degrees(math.atan2(dy,dx))-base+540)%360-180
            if not (p['a0']<=a<=p['a1']): continue
            t=(a-p['a0'])/span; taper=math.sin(math.pi*min(1,max(0,t)))**.6
            mid=(p['ri']+p['ro'])/2; half=(p['ro']-p['ri'])/2*taper
            d=r-mid
            if abs(d)>half or half<.5: continue
            if p['dith']==1 and (x+y)%2: continue
            if p['dith']==2 and (x+2*y)%3: continue
            u=(d+half)/(2*half)  # 0 inner ->1 outer edge
            if f==4: col=HOT if u>.8 else ACC if u>.6 else SEC if u>.35 else PRIM if u>.15 else DARK
            elif f>=5: col=ACC if u>.7 else SEC if u>.4 else PRIM
            else: col=ACC if u>.75 else SEC if u>.45 else PRIM if u>.2 else DARK
            px[x,y]=col
    # sparks / dark motes
    for i in range(p['sp']):
        a=math.radians(base+rnd.uniform(p['a0'],p['a1']))
        r=rnd.uniform(p['ri']-3 if f<=2 else p['ro']-2,p['ro']+(2 if f<4 else 5))
        x,y=int(C+math.cos(a)*r),int(C+math.sin(a)*r)
        col=rnd.choice([ACC,HOT,SEC] if f in(4,5) else [PRIM,SEC,ACC])
        for ox,oy in ([(0,0),(1,0),(0,1),(1,1)] if f==4 and i%3==0 else [(0,0)]):
            if 0<=x+ox<S and 0<=y+oy<S: px[x+ox,y+oy]=col
    if f==1:  # charge core
        for ox,oy in [(0,0),(1,0),(0,1),(1,1)]: px[C-1+ox,C-1+oy]=SEC
        px[C-1,C-1]=ACC
    return im
sheet=Image.new("RGBA",(S*6,S*4),(0,0,0,0))
for row,base in enumerate([90,270,180,0]):  # S,N,W,E
    for f in range(1,7): sheet.paste(frame(f,base),((f-1)*S,row*S))
sheet.save("sinful_counter_slash_288x192.png")
sheet.resize((288*4,192*4),Image.NEAREST).save("preview_x4.png")
print("ok")
