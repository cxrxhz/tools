import json
import originpro as op

path = r'F:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\Cr2Te3_LFA_4.22.opju'
op.set_show(False)
opened = op.open(path, readonly=True, asksave=False)
if not opened:
    raise SystemExit('FAILED_TO_OPEN')

wks = op.find_sheet('w', '[Book1]Sheet1')
if wks is None:
    raise SystemExit('BOOK1_SHEET1_NOT_FOUND')

ncols = wks.cols
first_long = wks.get_label(0, 'L')
last_long = wks.get_label(ncols - 1, 'L')
rows = []
for r in range(6):
    rows.append({
        'row': r + 1,
        'B': wks.cell(r, 1),
        'G': wks.cell(r, 6),
        'H': wks.cell(r, 7),
    })

g = op.find_graph('Graph1')
if g is None:
    raise SystemExit('GRAPH1_NOT_FOUND')
lay = g[0]
plots = lay.plot_list()
plot_info = []
for i, p in enumerate(plots, 1):
    info = {
        'index': i,
        'name': p.name,
        'lname': getattr(p, 'lname', ''),
        'range': p.lt_range(),
    }
    for prop in ['name', 'dataset', 'range', 'input', 'x.from', 'y.from']:
        try:
            info[f'prop:{prop}'] = p.get_str(prop)
        except Exception:
            pass
    plot_info.append(info)

result = {
    'opened': opened,
    'col_count': ncols,
    'first_long_name': first_long,
    'last_long_name': last_long,
    'rows_B_G_H': rows,
    'graph1_plots': plot_info,
}
print(json.dumps(result, ensure_ascii=False, indent=2))

op.exit()
