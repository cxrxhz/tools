import numpy as np
np.random.seed(42)

def k_eff(E=0.0, f=0.0, alpha=0.0):
    base = 1.0 + 1.8*f
    gain = 0.35*E*(0.5+f)
    coup = 0.55*alpha*E
    penalty = 0.15*(E**2)*(1.0-alpha)
    noise = np.random.normal(0, 0.015)
    return base + gain + coup - penalty + noise

N=200
settings=[
    ('S0_baseline_no_field',0.0,0.45,0.00),
    ('S1_field_only',0.8,0.45,0.00),
    ('S2_field_plus_coupling',0.8,0.45,0.65),
    ('S3_field_plus_coupling_plus_interface_design',0.8,0.70,0.65),
]
vals=[]
for name,E,f,a in settings:
    arr=np.array([k_eff(E,f,a) for _ in range(N)])
    vals.append((name,arr.mean(),arr.std(ddof=1)))
base=vals[0][1]
print('ToyPilotResults')
for name,m,s in vals:
    rel=(m-base)/base*100
    print(f'{name}\tmean={m:.4f}\tstd={s:.4f}\trel_vs_S0={rel:+.2f}%')
