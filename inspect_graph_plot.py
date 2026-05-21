import json
import originpro as op
path = r'F:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\Cr2Te3_LFA_4.22.opju'
op.set_show(False)
op.open(path, readonly=True, asksave=False)
g = op.find_graph('Graph1')
lay = g[0]
p = lay.plot_list()[0]
print('plot_name', p.name)
print('plot_lname', p.lname)
print('plot_lt_range', p.lt_range())
for prop in ['name','data.name','data.x.name','data.y.name','xdataset','ydataset','source','range1','input','x.from','y.from']:
    try:
        print(prop, '=>', p.get_str(prop))
    except Exception as e:
        print(prop, 'ERR', type(e).__name__, e)
try:
    print('usertree', p.usertree)
except Exception as e:
    print('usertree ERR', e)
try:
    print('comments', p.comments)
except Exception as e:
    print('comments ERR', e)
op.exit()
