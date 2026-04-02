"""Generate menu_icon.png for Git Dashboard tray icon."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QBrush, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF

app = QApplication(sys.argv)

SIZE = 1024
pix = QPixmap(SIZE, SIZE)
pix.fill(QColor(0, 0, 0, 0))

p = QPainter(pix)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

S = SIZE

# ── Background: rounded square ──────────────────────────────────────
bg_rect = QRectF(S * 0.06, S * 0.06, S * 0.88, S * 0.88)
bg_path = QPainterPath()
bg_path.addRoundedRect(bg_rect, S * 0.18, S * 0.18)

p.setBrush(QBrush(QColor("#0f0f1a")))
p.setPen(Qt.PenStyle.NoPen)
p.drawPath(bg_path)

# ── Git branch icon ──────────────────────────────────────────────────
# Node positions (main: bottom-left, branch: top-right, top: top-left)
main_x, main_y   = S * 0.32, S * 0.72   # main branch node (bottom)
top_x,  top_y    = S * 0.32, S * 0.28   # main branch node (top)
branch_x, branch_y = S * 0.68, S * 0.40 # feature branch node

# Line: main vertical
pen_line = QPen(QColor("#334155"))
pen_line.setWidthF(S * 0.055)
pen_line.setCapStyle(Qt.PenCapStyle.RoundCap)
p.setPen(pen_line)
p.setBrush(Qt.BrushStyle.NoBrush)
p.drawLine(QPointF(main_x, main_y), QPointF(top_x, top_y))

# Curve: branch off from top node to branch node
curve_pen = QPen(QColor("#0ea5e9"))
curve_pen.setWidthF(S * 0.055)
curve_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
p.setPen(curve_pen)

curve = QPainterPath()
curve.moveTo(top_x, top_y)
ctrl1 = QPointF(top_x, top_y + (branch_y - top_y) * 0.5)
ctrl2 = QPointF(branch_x - (branch_x - top_x) * 0.3, branch_y)
curve.cubicTo(ctrl1, ctrl2, QPointF(branch_x, branch_y))
p.drawPath(curve)

# Node sizes
NODE_R = S * 0.085

# Main bottom node — filled sky blue
p.setPen(Qt.PenStyle.NoPen)
p.setBrush(QBrush(QColor("#0ea5e9")))
p.drawEllipse(QPointF(main_x, main_y), NODE_R, NODE_R)

# Top node — filled white-ish
p.setBrush(QBrush(QColor("#e2e8f0")))
p.drawEllipse(QPointF(top_x, top_y), NODE_R, NODE_R)

# Branch node — ring (accent light)
ring_pen = QPen(QColor("#38bdf8"))
ring_pen.setWidthF(S * 0.048)
p.setPen(ring_pen)
p.setBrush(QBrush(QColor("#082f49")))
p.drawEllipse(QPointF(branch_x, branch_y), NODE_R, NODE_R)

p.end()

out = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources", "icons", "menu_icon.png"
)
pix.save(out, "PNG")
print(f"Saved: {out}")
