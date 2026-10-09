"""Modelos locais explícitos, unidades N/mm/MPa. Referências em METODOLOGIA.md."""
import math


def grip_factor(grip, db):
    """NBR 8800:2024, 6.3.7; sem dispensar redução por protensão."""
    return max(0.0, 1.0 - 0.01 * max(0.0, grip - 5*db)/1.5)


def elastic_group(n, pitch, columns, gauge, V, N, M):
    coords=[((j-(columns-1)/2)*gauge,(i-(n-1)/2)*pitch)
            for j in range(columns) for i in range(n)]
    J=sum(x*x+y*y for x,y in coords)
    if J<=0: raise ValueError("Grupo degenerado")
    nb=len(coords)
    return [(N/nb-M*y/J,V/nb+M*x/J) for x,y in coords]


def elastic_moment_bound(n,pitch,columns,gauge,nominal_bolt):
    """Limite inferior elástico, sem ganho de redistribuição do CIR."""
    radii=[math.hypot((j-(columns-1)/2)*gauge,(i-(n-1)/2)*pitch)
           for j in range(columns) for i in range(n)]
    return nominal_bolt*sum(r*r for r in radii)/max(radii)


def pure_moment_coefficient(n,pitch,columns,gauge):
    """C' pelo CIR centrado: Muir/Hewitt (2009), Δmax = 0,34 pol.
    Retorna comprimento na unidade de pitch/gauge. Lei usa Δ em polegadas.
    """
    radii=[math.hypot((j-(columns-1)/2)*gauge,(i-(n-1)/2)*pitch)
           for j in range(columns) for i in range(n)]
    rmax=max(radii)
    return sum(r*(1-math.exp(-3.4*r/rmax))**.55 for r in radii)


def rectangle_section(rectangles):
    """Retângulos (y0,y1,largura), sem sobreposição; y medido do topo."""
    area=sum((b-a)*w for a,b,w in rectangles)
    if area<=0: raise ValueError("Seção vazia")
    yc=sum((b*b-a*a)*w/2 for a,b,w in rectangles)/area
    inertia=sum(w*((b-yc)**3-(a-yc)**3)/3 for a,b,w in rectangles)
    lo=min(a for a,b,w in rectangles);hi=max(b for a,b,w in rectangles)
    S=inertia/max(yc-lo,hi-yc)
    left=lo;right=hi
    for _ in range(65):
        mid=(left+right)/2
        below=sum(max(0,min(mid,b)-a)*w for a,b,w in rectangles)
        if below<area/2:left=mid
        else:right=mid
    yp=(left+right)/2
    fun=lambda y:.5*y*abs(y)
    Z=sum(w*(fun(b-yp)-fun(a-yp)) for a,b,w in rectangles)
    return dict(A=area,yc=yc,I=inertia,S=S,Z=Z)


def coped_section(profile,top,bottom,holes=()):
    """Seção remanescente; raios ignorados conservadoramente."""
    low=top;high=profile.d-bottom
    points=sorted(set([low,high]+[v for v in (profile.tf,profile.d-profile.tf) if low<v<high]+[v for a,b in holes for v in (a,b) if low<v<high]))
    rectangles=[]
    for a,b in zip(points,points[1:]):
        y=(a+b)/2
        w=profile.bf if y<profile.tf or y>profile.d-profile.tf else profile.tw
        if any(x<=y<=z for x,z in holes):w-=profile.tw
        if w>0:rectangles.append((a,b,w))
    return rectangle_section(rectangles)


def single_cope_moment(d,h,tw,length,fy,S,Z,E=200000):
    """AISC Manual 16 Parte 9; P901 II.A-6; Dowswell EJ 2018."""
    f=2*length/d if length<=d else min(3,1+length/d)
    k=2.2*(h/length)**(1.65 if length<=h else 1)
    k1=max(1.61,f*k);lam=h/tw;lp=.475*math.sqrt(k1*E/fy)
    Mp=fy*Z;My=fy*S
    if lam<=lp:Mn=Mp
    elif lam<=2*lp:Mn=Mp-(Mp-My)*(lam/lp-1)
    else:Mn=.903*E*k1/lam**2*S
    return max(0,min(Mp,Mn)),dict(k1=k1,lam=lam,lp=lp,My=My,Mp=Mp)


def web_shear(h,tw,fy,E=200000,gamma=1.1,kv=5.34):
    """Alma sem enrijecedores transversais, kv=5,34 para I e 1,2 para T; NBR 5.4.3."""
    lam=h/tw;lp=1.1*math.sqrt(kv*E/fy);lr=1.37*math.sqrt(kv*E/fy)
    cv=1 if lam<=lp else lp/lam if lam<=lr else 1.24*(lp/lam)**2
    return .6*fy*h*tw*cv/gamma,cv


def required_development_weld(tp,fy,fw):
    """Regra AISC 5t/8, ampliada por razão resistente para aços/eletrodos."""
    return max(.625*tp,math.sqrt(3)/2*tp*fy/fw)
