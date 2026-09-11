"""Create a portable PNG report from the applied financial result."""
from io import BytesIO
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont


def render_report(frame, company, frequency, unit, groups, colors):
    font_path = str(Path(__file__).parent / "assets" / "NotoSansKR.ttf")
    fonts = {size: ImageFont.truetype(font_path, size) for size in (20, 23, 26, 32, 44)}
    width = max(1800, 240 + len(frame) * 100)
    image = Image.new("RGB", (width, 2010), "#F5F7FA")
    draw = ImageDraw.Draw(image)

    def text(x, y, value, size=23, color="#191F28", anchor=None):
        draw.text((x, y), str(value), font=fonts[size], fill=color, anchor=anchor)

    text(64, 38, f"{company} · 기업 재무 대시보드", 44)
    text(64, 108, f"{frequency}  |  {frame.index[0]} ~ {frame.index[-1]}  |  단위: {unit}", 26)
    text(64, 155, "DART·SEC 공식 공시 기반 · 표시 단위와 보고기간을 함께 확인하세요.", 23, "#6B7684")
    for index, (title, names) in enumerate(groups):
        top = 225 + index * 570
        draw.rounded_rectangle((40, top, width - 40, top + 540), radius=22, fill="white")
        text(68, top + 22, title, 32)
        # Two legend rows for cash flow; separate from plot and period labels.
        for j, (name, color) in enumerate(zip(names, colors)):
            lx = 72 + (j % 3) * ((width - 150) / 3)
            ly = top + 84 + (j // 3) * 36
            draw.rounded_rectangle((lx, ly + 8, lx + 19, ly + 27), radius=3, fill=color)
            text(lx + 30, ly, name, 23)
        left, right, upper, lower = 165, width - 78, top + 177, top + 455
        values = frame[names].to_numpy()
        low, high = min(0, float(values.min())), max(0, float(values.max()))
        span = high - low or 1
        step = 10 ** math.floor(math.log10(span / 4))
        step *= next(v for v in (1, 2, 5, 10) if v * step >= span / 4)
        low, high = math.floor(low / step) * step, math.ceil(high / step) * step
        if low == high:
            high = low + step

        def y(value):
            return lower - (value - low) / (high - low) * (lower - upper)

        for k in range(round((high - low) / step) + 1):
            tick = low + k * step
            line_y = y(tick)
            draw.line((left, line_y, right, line_y), fill="#D5DCE5" if tick == 0 else "#EEF1F4", width=2)
            text(left - 16, line_y, f"{tick:,.0f}", 20, "#6B7684", "rm")
        group_width = (right - left) / len(frame)
        bar_width = group_width * .78 / len(names)
        for i, period in enumerate(frame.index):
            start = left + i * group_width + group_width * .11
            for j, color in enumerate(colors[:len(names)]):
                value = float(values[i, j])
                if value:
                    x = start + j * bar_width
                    draw.rectangle((x, min(y(0), y(value)), x + max(1, bar_width - 2), max(y(0), y(value))), fill=color)
            text(left + (i + .5) * group_width, lower + 22, period, 20, "#6B7684", "mt")
    text(64, 1950, "모든 항목을 포함한 조회 결과입니다. 화면에서 범례로 숨긴 항목도 저장됩니다.", 23, "#6B7684")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
