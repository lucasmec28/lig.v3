"""Contornos e propriedades geométricas; não atribui resistência a enrijecedores."""
def plate_outline(c):
    """Coordenadas x desde a face do apoio e y desde o topo do apoio."""
    level=c.beam_level if c.kind=='beam_web' else 0
    top=level+c.plate_top;bottom=top+c.hp
    if not c.full_depth:return [(0,top),(c.width,top),(c.width,bottom),(0,bottom)]
    a=c.support.tf;b=c.support.d-c.support.tf;q=c.root_width;k=c.corner_clip
    return [(k,a),(q,a),(q,top),(c.width,top),(c.width,bottom),
            (q,bottom),(q,b),(k,b),(0,b-k),(0,a+k)]


def stiffener_outline(c):
    a=c.support.tf;b=c.support.d-c.support.tf;q=c.stiffener_width;k=c.corner_clip
    face=-c.support.tw
    return [(face-k,a),(face-q,a),(face-q,b),(face-k,b),(face,b-k),(face,a+k)]


def polygon_area(points):
    return abs(sum(x*y2-x2*y for (x,y),(x2,y2) in zip(points,points[1:]+points[:1])))/2
