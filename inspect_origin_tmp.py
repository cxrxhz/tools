import originpro as op
from pathlib import Path
path = r"f:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\Cr2Te3_LFA_4.22_calculated.opju"
print('exists', Path(path).exists())
print('open', op.open(path, readonly=True))
for i in range(10):
    wb = op.find_book('w', i)
    if not wb:
        break
    print('WB', i, wb.name, wb.lname)
    try:
        for j in range(10):
            wks = op.find_sheet('w', f'[{wb.name}]{j+1}')
            if not wks:
                break
            print('  WKS', j, wks.name, wks.lname, 'shape', wks.shape)
    except Exception as e:
        print('  sheet err', e)
for i in range(10):
    gp = op.find_graph(i)
    if not gp:
        break
    print('GP', i, gp.name, gp.lname)
    try:
        lay = gp[0]
        plots = lay.plot_list()
        print('  plots', len(plots))
        for k,p in enumerate(plots):
            print('   plot', k, 'name', p.name, 'lname', p.lname, 'lt_range', p.lt_range())
            print('   obj type', type(p.obj))
            print('   obj attrs sample', [n for n in dir(p.obj) if 'range' in n.lower() or 'data' in n.lower() or 'work' in n.lower() or 'col' in n.lower()][:50])
    except Exception as e:
        print('  graph err', e)
op.exit()
