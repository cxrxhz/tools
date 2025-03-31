from pptx import Presentation


def main():
    prs = Presentation("template.pptx")

    # 遍历所有布局，仅打印能访问 placeholder_format 的形状（即占位符）
    for layout_index, layout in enumerate(prs.slide_layouts):
        print(f"\n布局索引 {layout_index}: 名称 = {layout.name}")
        print("该布局中存在以下占位符：")
        for shape_index, shape in enumerate(layout.shapes):
            try:
                # 尝试访问 placeholder_format 属性
                ph = shape.placeholder_format  # 如果不是占位符，则会抛出异常
                print(f"  形状索引 {shape_index}: 名称='{shape.name}'")
            except Exception:
                # 忽略那些不是占位符的形状
                continue


if __name__ == "__main__":
    main()
