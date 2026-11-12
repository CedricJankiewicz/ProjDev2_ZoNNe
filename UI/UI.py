import math
import tkinter as tk
import customtkinter as ctk
from dataclasses import dataclass

BG = "#ffffff"
BAR = "#f3f3f8"
CANVAS_BG = "#fafafd"
CANVAS_BORDER = "#d0d0dc"
ZONE_LINE = "#dcdce8"
TEXT = "#2a2a3c"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9279ff"
INACTIVE = "#e2e2ee"
RED = "#ff4d6d"
BLUE = "#4d9bff"
COLORS = {0: RED, 1: BLUE}   # label -> color
POINT_RADIUS = 13
MARGIN = 6
MIN_DIST = 2 * POINT_RADIUS + 1
FORBIDDEN = "#b0b0b8"
DEBUG = True

class ColorSelector(ctk.CTkFrame):
    """Circles used to choose the label (class) of the next point."""

    def __init__(self, parent, labels=(0, 1)):
        super().__init__(parent, fg_color="transparent")
        self.label = labels[0]
        self.circles = {}

        for label in labels:
            cv = tk.Canvas(self, width=50, height=50, bg=BAR, highlightthickness=0, cursor="hand2")
            cv.pack(side="left", padx=10)
            circle_id = cv.create_oval(6, 6, 44, 44, fill=COLORS[label], outline=BAR, width=3)
            cv.bind("<Button-1>", lambda event, l=label: self.select(l))
            self.circles[label] = (cv, circle_id)

        self.select(self.label)

    def select(self, label):
        self.label = label
        for l, (cv, circle_id) in self.circles.items():
            cv.itemconfig(circle_id, outline=TEXT if l == label else BAR)

class NeuronSlider(ctk.CTkFrame):
    """Label 'neurons : n' with a slider below it."""

    def __init__(self, parent, min_value=1, max_value=16, default=8):
        super().__init__(parent, fg_color="transparent")
        self.text = ctk.StringVar()
        self.label = ctk.CTkLabel(self, textvariable=self.text, text_color=TEXT, font=ctk.CTkFont("Segoe UI", 14))
        self.label.pack()
        self.slider = ctk.CTkSlider(self, from_=min_value, to=max_value, number_of_steps=max_value - min_value, width=180,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER, progress_color=ACCENT, fg_color=INACTIVE, command=self._update)
        self.slider.pack(pady=(4, 0))
        self.slider.set(default)
        self._update(default)

    def _update(self, value):
        self.text.set(f"neurons : {int(value)}")

    @property
    def value(self):
        return int(self.slider.get())


class Spinner(tk.Canvas):
    """Loading indicator made of dots that fade around a circle."""

    TRAIL = [ACCENT, "#9279ff", "#b3a3ff", "#cfc6ff"]
    def __init__(self, parent, size=50, dots=8):
        super().__init__(parent, width=size, height=size, bg=BAR,
                         highlightthickness=0)
        self.dots = dots
        self.step = 0
        self.running = False
        self.items = []

        center = size / 2
        radius = size / 2 - 7
        for i in range(dots):
            angle = 2 * math.pi * i / dots
            x = center + radius * math.cos(angle)
            y = center + radius * math.sin(angle)
            self.items.append(self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=INACTIVE, outline=""))

    def start(self):
        if not self.running:
            self.running = True
            self._animate()

    def stop(self):
        self.running = False
        for item in self.items:
            self.itemconfig(item, fill=INACTIVE)

    def _animate(self):
        if not self.running:
            return
        for i, item in enumerate(self.items):
            age = (self.step - i) % self.dots
            color = self.TRAIL[age] if age < len(self.TRAIL) else INACTIVE
            self.itemconfig(item, fill=color)
        self.step += 1
        self.after(100, self._animate)

@dataclass
class Point:
    x: float
    y: float
    label: int
    item: int

class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("ZoNNe")
        self.geometry("900x600")
        self.minsize(600, 400)

        self.points = []

        self.bar = ctk.CTkFrame(self, height=90, corner_radius=0, fg_color=BAR)
        self.bar.pack(side="bottom", fill="x")
        self.bar.pack_propagate(False)

        self.canvas = tk.Canvas(self, bg=CANVAS_BG, highlightthickness=1, highlightbackground=CANVAS_BORDER, cursor="crosshair")
        self.canvas.pack(side="top", fill="both", expand=True, padx=15, pady=15)

        self.ghost = self.canvas.create_oval(0, 0, 0, 0, width=2, state="hidden")

        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda e: self.hide_ghost())
        self.canvas.bind("<Button-1>", self.add_point)      # left click
        self.canvas.bind("<Button-3>", self.remove_point)   # right click
        self.canvas.bind("<Configure>", lambda e: self.draw_zone())

        self.selector = ColorSelector(self.bar)
        self.selector.pack(side="left", padx=20)

        self.slider = NeuronSlider(self.bar)
        self.slider.pack(side="left", padx=30)

        self.spinner = Spinner(self.bar)
        self.spinner.pack(side="right", padx=20)

        self.start_button = ctk.CTkButton(self.bar, text="start", width=140, height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont("Segoe UI", 15, "bold"), command=self.on_start)
        self.start_button.pack(side="right", padx=20)

    def draw_zone(self):
        """Dashed rectangle showing where points can be placed."""

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.delete("zone")
        self.canvas.create_rectangle(MARGIN, MARGIN, w - MARGIN, h - MARGIN, outline=ZONE_LINE, dash=(4, 4), tags="zone")
        self.canvas.tag_lower("zone")

    def clamp(self, x, y):
        """Push a position inside the canvas so the whole point is visible."""

        limit = MARGIN + POINT_RADIUS
        x = min(max(x, limit), self.canvas.winfo_width() - limit)
        y = min(max(y, limit), self.canvas.winfo_height() - limit)
        return x, y

    def is_free(self, x, y):
        """True if a point at (x, y) would not touch another point."""

        return all(math.hypot(x - p.x, y - p.y) >= MIN_DIST
                   for p in self.points)

    def point_at(self, x, y):
        """Return the point under (x, y), or None."""
        for p in reversed(self.points):
            if math.hypot(x - p.x, y - p.y) <= POINT_RADIUS:
                return p
        return None

    def hide_ghost(self):
        self.canvas.itemconfig(self.ghost, state="hidden")

    def on_motion(self, event):
        """Move the ghost; show an X cursor when no point can be placed."""

        if self.point_at(event.x, event.y) is not None:
            self.hide_ghost()
            self.canvas.config(cursor="X_cursor")
            return
        x, y = self.clamp(event.x, event.y)
        free = self.is_free(x, y)
        color = COLORS[self.selector.label] if free else FORBIDDEN
        self.canvas.config(cursor="crosshair" if free else "X_cursor")
        r = POINT_RADIUS
        self.canvas.coords(self.ghost, x - r, y - r, x + r, y + r)
        self.canvas.itemconfig(self.ghost, outline=color, state="normal")
        self.canvas.tag_raise(self.ghost)

    def add_point(self, event):
        x, y = self.clamp(event.x, event.y)
        if not self.is_free(x, y):
            return
        label = self.selector.label
        r = POINT_RADIUS
        item = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=COLORS[label], outline="")
        p = Point(x, y, label, item)
        self.points.append(p)
        self.canvas.tag_raise(self.ghost)
        if DEBUG:
            print(f"Point added: x={p.x}, y={p.y}, value={p.label} \n")
            print(self.points)
        self.on_motion(event)
    def remove_point(self, event):
        """Right click: delete the point under the cursor."""

        p = self.point_at(event.x, event.y)
        if p is not None:
            self.canvas.delete(p.item)
            self.points.remove(p)
            self.on_motion(event)

    def on_start(self):
        if self.spinner.running:
            self.spinner.stop()
            self.start_button.configure(text="start")
        else:
            self.spinner.start()
            self.start_button.configure(text="stop")
            # TODO: train the neural network here with
            # (p.x, p.y)
