"""Freistellen: entfernt einen naeher-am-weissen Canvas-Hintergrund liegenden,
mit dem Bild verbundenen Bereich per Flood-Fill und entfernt dabei per
Un-Premultiply auch den weissen Fransen-/Halo-Saum an den Kanten.
Motiv bleibt unveraendert; nur Hintergrund/Rand wird transparent."""
import sys, math
from collections import deque
from PIL import Image


def defringe(path, out_path, bg=None, bg_thresh=60):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()

    if bg is None:
        # Referenz-Hintergrund aus den vier Ecken (falls dort opak) oder Default-Weiss.
        samples = []
        for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            r, g, b, a = px[cx, cy]
            if a > 0:
                samples.append((r, g, b))
        if samples:
            bg = tuple(sum(c[i] for c in samples) / len(samples) for i in range(3))
        else:
            bg = (248.0, 247.0, 247.0)

    def dist(c):
        return math.sqrt(sum((c[i] - bg[i]) ** 2 for i in range(3)))

    def passable(x, y):
        r, g, b, a = px[x, y]
        if a == 0:
            return True, 0.0
        d = dist((r, g, b))
        if d < bg_thresh:
            return True, d
        return False, None

    visited = [[False] * w for _ in range(h)]
    dist_map = [[0.0] * w for _ in range(h)]
    q = deque()

    def seed(x, y):
        if not visited[y][x]:
            ok, d = passable(x, y)
            if ok:
                visited[y][x] = True
                dist_map[y][x] = d
                q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                ok, d = passable(nx, ny)
                if ok:
                    visited[ny][nx] = True
                    dist_map[ny][nx] = d
                    q.append((nx, ny))

    out = Image.new("RGBA", (w, h))
    outpx = out.load()
    feather = bg_thresh
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if visited[y][x]:
                d = dist_map[y][x]
                alpha = int(round(255 * min(1.0, d / feather)))
                if alpha <= 0:
                    outpx[x, y] = (0, 0, 0, 0)
                else:
                    af = alpha / 255.0
                    nr = (r - (1 - af) * bg[0]) / af
                    ng = (g - (1 - af) * bg[1]) / af
                    nb = (b - (1 - af) * bg[2]) / af
                    nr = max(0, min(255, round(nr)))
                    ng = max(0, min(255, round(ng)))
                    nb = max(0, min(255, round(nb)))
                    outpx[x, y] = (nr, ng, nb, alpha)
            else:
                outpx[x, y] = (r, g, b, 255)
    out.save(out_path, "PNG")
    return bg


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    thresh = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    used_bg = defringe(src, dst, bg_thresh=thresh)
    print("bg used:", used_bg, "->", dst)
