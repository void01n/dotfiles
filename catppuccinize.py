import sys, re
stops = [(138,173,244), (183,189,248), (245,189,230)]
def lerp(a, b, t):
    return tuple(round(a[i] + (b[i]-a[i])*t) for i in range(3))
def color_at(t):
    t = max(0.0, min(1.0, t))
    seg = t * (len(stops)-1)
    i = min(int(seg), len(stops)-2)
    return lerp(stops[i], stops[i+1], seg - i)

data = sys.stdin.read()
data = re.sub(r"\x1b\[[0-9;]*m", "", data)
lines = data.split("\n")
n_lines = max(len(lines), 1)
max_width = max((len(l) for l in lines), default=1) or 1
single_line = n_lines == 1

out_lines = []
for row, line in enumerate(lines):
    chars = []
    for col, ch in enumerate(line):
        if ch == " ":
            chars.append(ch)
            continue
        if single_line:
            t = col / max_width
        else:
            t = (row / n_lines) * 0.8 + (col / max_width) * 0.2
        r, g, b = color_at(t)
        chars.append(f"\x1b[38;2;{r};{g};{b}m{ch}")
    out_lines.append("".join(chars) + "\x1b[0m")
sys.stdout.write("\n".join(out_lines))
