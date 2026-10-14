# Natural Ink

让文字和公式更像手写，同时控制随机性，保持可读性。[English](README.md)

目前支持：

- Caveat 的真实替代字形、轻微轮廓变化、大小与位置变化。
- 48 种数学符号笔画：等号两条线不等长，横线有弧度，笔画有轻微粗细变化。
- 固定种子的可复现 PDF 生成，正文变形幅度默认 0.4。
- PDF 笔迹中心线重建、可编辑 JSON、PDF/SVG 预览。
- **实验性 `.goodnotes` 原生笔迹导出**。

## 验证边界

生成的原生文件包含笔迹记录，独立解析器已能读回页面、颜色、线宽和坐标。**尚未在 Goodnotes 应用里确认导入、擦除、套索和保存。** 解析成功不能代替应用实测。

PDF 重建的轨迹也不等于原始落笔顺序：一个字可能被拆成多条路径；原生文件目前每条路径使用中位笔宽，不能完整保留压感。不要把这个功能宣传成“完美 PDF 转 Goodnotes”。

## 使用

安装 Python 3.12+ 和 uv 后：

```sh
git clone https://github.com/LambertAlpha/natural-ink.git
cd natural-ink
uv sync --locked
uv run natural-ink render examples/demo.json -o output/demo.pdf --seed 183 --variation 0.4
uv run natural-ink trace output/demo.pdf -o output/demo.ink.json
uv run natural-ink preview output/demo.ink.json -o output/reconstructed.pdf
uv run natural-ink export output/demo.ink.json -o output/demo.goodnotes --experimental
```

先在 Goodnotes 导入这个小样，检查是否能擦掉部分笔画、套索移动，再保存、关闭、重新打开。验证后再尝试密集的多页笔记。

输入采用明确位置的 JSON 排版：左上角为原点，单位是 point（72 point = 1 英寸），文字 y 是基线。正文变形参数不影响公式笔画风格；设置为 0 仍保留字体本身的替代字形。当前没有自动换行或完整 LaTeX 排版。

PDF 重建适合浅色纸上的深色笔迹，会去掉浅灰网格并映射到指定颜色；不适合照片、深色背景或复杂图表。完整说明见 [README](README.md)。

代码 MIT；字体 SIL OFL。第三方运行依赖有各自许可，见 [NOTICE](NOTICE.md)。
