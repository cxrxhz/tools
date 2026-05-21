import originpro as op
path = r'F:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\Cr2Te3_LFA_4.22.opju'
op.set_show(False)
op.open(path, readonly=True, asksave=False)
p = op.find_graph('Graph1')[0].plot_list()[0]
attrs = [a for a in dir(p.obj) if any(k in a.lower() for k in ['data','range','wks','col','name'])]
print('\n'.join(attrs[:200]))
op.exit()
