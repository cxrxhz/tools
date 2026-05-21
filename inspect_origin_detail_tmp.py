import originpro as op
from pathlib import Path
path = r"f:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\Cr2Te3_LFA_4.22_calculated.opju"
assert Path(path).exists()
op.open(path, readonly=True)
wks = op.find_sheet('w', '[Book1]Sheet1')
print('sheet', wks.name, wks.lname, 'shape', wks.shape)
print('col_names', [wks.obj[i].GetName() for i in range(wks.cols)])
print('long_names', wks.get_labels('L'))
print('units', wks.get_labels('U'))
print('comments', wks.get_labels('C'))
print('rows0_5', wks.to_list2(0,5,0,wks.cols-1))

g = op.find_graph('Graph1')
lay = g[0]
p = lay.plot_list()[0]
print('plot name', p.name)
print('plot lname', p.lname)
print('dataset prop', getattr(p.obj,'DatasetName',None))
try:
    print('GetDatasetName', p.obj.GetDatasetName())
except Exception as e:
    print('GetDatasetName err', e)
for attr in ['Range']:
    try:
        val = getattr(p.obj, attr)
        print(attr, type(val), val)
        if hasattr(val,'GetRangeString'):
            print('  GetRangeString', val.GetRangeString())
        print('  attrs', [n for n in dir(val) if 'range' in n.lower() or 'col' in n.lower() or 'sheet' in n.lower() or 'book' in n.lower() or 'type' in n.lower() or 'x'==n.lower() or 'y'==n.lower()][:120])
    except Exception as e:
        print(attr, 'err', e)
try:
    rg = p.obj.GetRange()
    print('GetRange()', type(rg), rg)
    print('  attrs', [n for n in dir(rg) if 'range' in n.lower() or 'col' in n.lower() or 'sheet' in n.lower() or 'book' in n.lower() or 'type' in n.lower() or 'data' in n.lower() or n in ['X','Y','Z']][:120])
    for sub in ['GetRangeString','GetType','GetSubType','GetDataFormat','GetBook','GetSheet','GetXColumn','GetYColumn','GetErrColumn','GetXRange','GetYRange','GetZRange']:
        if hasattr(rg, sub):
            try:
                print(' ', sub, getattr(rg, sub)())
            except Exception as e:
                print(' ', sub, 'err', e)
except Exception as e:
    print('GetRange err', e)
op.exit()
