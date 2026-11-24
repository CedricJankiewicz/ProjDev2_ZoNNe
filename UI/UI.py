import math
import tkinter as tk
import customtkinter as ctk
from dataclasses import dataclass
from tkinter import messagebox
import os
from datetime import datetime
from .fake import fake_grid
from .storage import write_csv, read_csv

BG = "#ffffff"
BAR = "#f3f3f8"
CANVAS_BG = "#fafafd"
CANVAS_BORDER = "#d0d0dc"
TEXT = "#2a2a3c"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9279ff"
INACTIVE = "#e2e2ee"
RED = "#ff4d6d"
BLUE = "#4d9bff"
PALE = "#f4f0fa"
COLORS = {0: BLUE, 1: RED}
POINT_RADIUS = 13
MARGIN = 6
MIN_DIST = 2 * POINT_RADIUS + 1
FORBIDDEN = "#b0b0b8"
GRID_LINE = "#e6e6f4"
GRID_SIZE = 16
POINT_OUTLINE = "#000000"
DEBUG = False


def hex_to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))

def mix(color_a, color_b, t):
    """Blend two '#rrggbb' colors (t=0 -> a, t=1 -> b)."""
    rgb_a, rgb_b = hex_to_rgb(color_a), hex_to_rgb(color_b)
    r, g, b = (round(ca + (cb - ca) * t) for ca, cb in zip(rgb_a, rgb_b))
    return f"#{r:02x}{g:02x}{b:02x}"

def value_to_color(value):
    """0 -> blue, 0.5 -> pale (undecided), 1 -> red."""
    value = min(max(value, 0.0), 1.0)
    if value < 0.5:
        return mix(COLORS[0], PALE, value * 2)
    return mix(PALE, COLORS[1], (value - 0.5) * 2)

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
        self.geometry("1500x900")
        self.resizable(False, False)

        self.points = []
        self.image_item = None
        self.image = None
        self.cursor = "crosshair"
        self.last_grid = None
        self.cols = self.rows = 0
        self.zone_x = self.zone_y = MARGIN
        self.zone_w = self.zone_h = 0

        self.bar = ctk.CTkFrame(self, height=90, corner_radius=0, fg_color=BAR)
        self.bar.pack(side="bottom", fill="x")
        self.bar.pack_propagate(False)

        self.canvas = tk.Canvas(self, bg=CANVAS_BG, highlightthickness=1, highlightbackground=CANVAS_BORDER, cursor="crosshair")
        self.canvas.pack(side="top", fill="both", expand=True, padx=15, pady=15)

        self.ghost = self.canvas.create_oval(0, 0, 0, 0, width=2, state="hidden")

        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda e: self.hide_ghost())
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", self.remove_point)
        self.canvas.bind("<Configure>", lambda e: self.draw_zone())

        self.selector = ColorSelector(self.bar)
        self.selector.pack(side="left", padx=20)

        self.slider = NeuronSlider(self.bar)
        self.slider.pack(side="left", padx=30)

        self.clear_button = ctk.CTkButton(
            self.bar, text="clear", width=100, height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont("Segoe UI", 15, "bold"), command=self.clear_points)
        self.clear_button.pack(side="left", padx=(20, 5))

        self.save_button = ctk.CTkButton(
            self.bar, text="save", width=100, height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont("Segoe UI", 15, "bold"), command=self.save_points)
        self.save_button.pack(side="left", padx=(20, 5))

        self.load_button = ctk.CTkButton(
            self.bar, text="load", width=100, height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont("Segoe UI", 15, "bold"), command=self.load_points)
        self.load_button.pack(side="left", padx=(5, 20))

        self.spinner = Spinner(self.bar)
        self.spinner.pack(side="right", padx=20)

        self.start_button = ctk.CTkButton(self.bar, text="start", width=140, height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont("Segoe UI", 15, "bold"), command=self.on_start)
        self.start_button.pack(side="right", padx=20)

    # ---------- the grid (one rectangle per square) ----------

    def update_zone(self):
        """Fit a whole number of squares in the canvas and center the zone."""
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.cols = max(1, (w - 2 * MARGIN) // GRID_SIZE)
        self.rows = max(1, (h - 2 * MARGIN) // GRID_SIZE)
        self.zone_w = self.cols * GRID_SIZE
        self.zone_h = self.rows * GRID_SIZE
        self.zone_x = (w - self.zone_w) // 2
        self.zone_y = (h - self.zone_h) // 2

    def draw_zone(self):
        """Square grid lines, snapped to whole squares."""
        self.update_zone()
        self.canvas.delete("grid", "prediction")
        self.image_item = None
        x0, y0 = self.zone_x, self.zone_y
        x1, y1 = x0 + self.zone_w, y0 + self.zone_h

        for i in range(self.cols + 1):
            x = x0 + i * GRID_SIZE
            self.canvas.create_line(x, y0, x, y1, fill=GRID_LINE, tags="grid")
        for j in range(self.rows + 1):
            y = y0 + j * GRID_SIZE
            self.canvas.create_line(x0, y, x1, y, fill=GRID_LINE, tags="grid")
        self.canvas.tag_lower("grid")

        # keep the colors if the last grid has the right size
        if (self.last_grid and len(self.last_grid) == self.rows
                and len(self.last_grid[0]) == self.cols):
            self.show_prediction(self.last_grid)

    def show_prediction(self, grid):
        """Color every square from grid[row][col] (values between 0 and 1)."""
        self.last_grid = grid

        # small image: 1 pixel per square, then zoomed to the square size
        small = tk.PhotoImage(master=self.canvas, width=self.cols, height=self.rows)
        rows = ["{" + " ".join(value_to_color(v) for v in line) + "}"
                for line in grid]
        small.put(" ".join(rows))
        self.image = small.zoom(GRID_SIZE)

        if self.image_item is None:
            self.image_item = self.canvas.create_image(
                self.zone_x, self.zone_y, anchor="nw", image=self.image,
                tags="prediction")
            self.canvas.tag_lower(self.image_item)  # under grid lines and points
        else:
            self.canvas.itemconfig(self.image_item, image=self.image)

    # ---------- helpers ----------

    def clamp(self, x, y):
        """Push a position inside the zone so the whole point is visible."""
        r = POINT_RADIUS
        x = min(max(x, self.zone_x + r), self.zone_x + self.zone_w - r)
        y = min(max(y, self.zone_y + r), self.zone_y + self.zone_h - r)
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

    # ---------- mouse events ----------

    def set_cursor(self, name):
        """Change the cursor only when it is different (cheaper)."""
        if name != self.cursor:
            self.cursor = name
            self.canvas.config(cursor=name)

    def on_motion(self, event):
        """Move the ghost; show an X cursor when no point can be placed."""

        if self.point_at(event.x, event.y) is not None:
            self.hide_ghost()
            self.set_cursor("X_cursor")
            return
        x, y = self.clamp(event.x, event.y)
        free = self.is_free(x, y)
        color = COLORS[self.selector.label] if free else FORBIDDEN
        self.set_cursor("crosshair" if free else "X_cursor")
        r = POINT_RADIUS
        self.canvas.coords(self.ghost, x - r, y - r, x + r, y + r)
        self.canvas.itemconfig(self.ghost, outline=color, state="normal")

    def create_point(self, x, y, label):
        """Draw a point on the canvas and store it in self.points."""
        r = POINT_RADIUS
        item = self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                       fill=COLORS[label], outline=POINT_OUTLINE)
        p = Point(x, y, label, item)
        self.points.append(p)
        self.canvas.tag_raise(self.ghost)
        return p

    def add_point(self, event):
        x, y = self.clamp(event.x, event.y)
        if not self.is_free(x, y):
            return
        p = self.create_point(x, y, self.selector.label)
        if DEBUG:
            print(f"Point added: x={p.x}, y={p.y}, value={p.label}")
        self.on_motion(event)

    def remove_point(self, event):
        """Right click: delete the point under the cursor."""

        p = self.point_at(event.x, event.y)
        if p is not None:
            self.canvas.delete(p.item)
            self.points.remove(p)
            self.on_motion(event)

    # ---------- actions ----------

    def on_start(self):
        if self.spinner.running:
            self.spinner.stop()
            self.start_button.configure(text="start")
        else:
            self.spinner.start()
            self.start_button.configure(text="stop")

            # convert data for neurones
            inputs = []
            outputs = []
            for point in self.points:
                cx = self.canvas.winfo_width()
                cy = self.canvas.winfo_height()
                inputs.append([point.x / cx, point.y / cy])
                outputs.append(point.label)

            # TODO use neurones
            print(inputs)
            print(outputs)

            # self.rows x self.cols values between 0 and 1
            self.show_prediction(fake_grid(self.rows, self.cols))

    def save_points(self):
        filename = ctk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=os.getcwd(),
            initialfile=f"points_{int(datetime.now().timestamp())}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return
        try:
            write_csv(filename, [(p.x, p.y, p.label) for p in self.points])
        except OSError:
            messagebox.showerror("Invalid Path", "Could not write the file.")

    def load_points(self):
        filename = ctk.filedialog.askopenfilename(
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            initialdir=os.getcwd()
        )
        if not filename:
            return
        try:
            rows = read_csv(filename, COLORS)
        except FileNotFoundError:
            messagebox.showerror("Invalid Path", "Please enter a valid path.")
            return
        except ValueError:
            messagebox.showerror("Corrupted File", "The file is corrupted or contains invalid data.")
            return

        # the file is valid: replace the current points
        for p in self.points:
            self.canvas.delete(p.item)
        self.points.clear()
        for x, y, label in rows:
            self.create_point(x, y, label)

    def clear_points(self):
        """Delete every point from the canvas and from the list."""
        for p in self.points:
            self.canvas.delete(p.item)
        self.points.clear()