import math
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import csv
from datetime import datetime

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
LABELS = {RED: 0, BLUE: 1}

POINT_RADIUS = 13
MARGIN = 6


class ColorSelector(ctk.CTkFrame):
    """Red / blue circles used to choose the class of the next point."""

    def __init__(self, parent, colors=(RED, BLUE)):
        super().__init__(parent, fg_color="transparent")
        self.color = colors[0]
        self.circles = {}

        for c in colors:
            cv = tk.Canvas(self, width=50, height=50, bg=BAR,
                           highlightthickness=0, cursor="hand2")
            cv.pack(side="left", padx=10)
            circle_id = cv.create_oval(6, 6, 44, 44, fill=c,
                                       outline=BAR, width=3)
            cv.bind("<Button-1>", lambda event, c=c: self.select(c))
            self.circles[c] = (cv, circle_id)

        self.select(self.color)

    def select(self, color):
        self.color = color
        for c, (cv, circle_id) in self.circles.items():
            cv.itemconfig(circle_id, outline=TEXT if c == color else BAR)


class NeuronSlider(ctk.CTkFrame):
    """Label 'neurons : n' with a slider below it."""

    def __init__(self, parent, min_value=1, max_value=16, default=5):
        super().__init__(parent, fg_color="transparent")
        self.text = ctk.StringVar()
        self.label = ctk.CTkLabel(self, textvariable=self.text, text_color=TEXT, font=ctk.CTkFont("Segoe UI", 14))
        self.label.pack()

        self.slider = ctk.CTkSlider(
            self, from_=min_value, to=max_value,
            number_of_steps=max_value - min_value, width=180,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            progress_color=ACCENT, fg_color=INACTIVE, command=self._update)
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
            self.items.append(
                self.create_oval(x - 4, y - 4, x + 4, y + 4,
                                 fill=INACTIVE, outline=""))

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


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("ZoNNe")
        self.geometry("900x600")

        self.points = []   # list of (x, y, color, canvas item id)

        # Bottom area: control bar (packed first so it keeps its space)
        self.bar = ctk.CTkFrame(self, height=90, corner_radius=0,
                                fg_color=BAR)
        self.bar.pack(side="bottom", fill="x")
        self.bar.pack_propagate(False)

        # Top area: drawing canvas
        self.canvas = tk.Canvas(self, bg=CANVAS_BG, highlightthickness=1,
                                highlightbackground=CANVAS_BORDER)
        self.canvas.pack(side="top", fill="both", expand=True,
                         padx=15, pady=15)
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", self.remove_point)   # right click
        self.canvas.bind("<Configure>", self.draw_zone)

        self.selector = ColorSelector(self.bar)
        self.selector.pack(side="left", padx=20)

        self.slider = NeuronSlider(self.bar)
        self.slider.pack(side="left", padx=30)

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

        self.start_button = ctk.CTkButton(
            self.bar, text="start", width=140, height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont("Segoe UI", 15, "bold"), command=self.on_start)
        self.start_button.pack(side="right", padx=20)

    def draw_zone(self, event=None):
        """Dashed rectangle showing where points can be placed."""
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.delete("zone")
        self.canvas.create_rectangle(MARGIN, MARGIN, w - MARGIN, h - MARGIN,
                                     outline=ZONE_LINE, dash=(4, 4),
                                     tags="zone")
        self.canvas.tag_lower("zone")

    def can_place(self, x, y):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        limit = MARGIN + POINT_RADIUS

        # Too close to the border
        if x < limit or x > w - limit or y < limit or y > h - limit:
            return False

        # Overlapping another point
        for px, py, _, _ in self.points:
            if math.hypot(x - px, y - py) < 2 * POINT_RADIUS:
                return False
        return True

    def add_point(self, event):
        if not self.can_place(event.x, event.y):
            return
        color = self.selector.color
        r = POINT_RADIUS
        item = self.canvas.create_oval(event.x - r, event.y - r,
                                       event.x + r, event.y + r,
                                       fill=color, outline="")
        self.points.append((event.x, event.y, color, item))

        label = LABELS[color]
        messagebox.showinfo(
            "Point added",
            f"x = {event.x}\ny = {event.y}\nvalue = {label}")

    def remove_point(self, event):
        """Right click: delete the point under the cursor."""
        for point in self.points:
            px, py, _, item = point
            if math.hypot(event.x - px, event.y - py) <= POINT_RADIUS + 2:
                self.canvas.delete(item)
                self.points.remove(point)
                return

    def on_start(self):
        if self.spinner.running:
            self.spinner.stop()
            self.start_button.configure(text="start")
        else:
            self.spinner.start()
            self.start_button.configure(text="stop")
            # TODO: train the neural network here with
            # self.points and self.slider.value neurons
            print(f"{len(self.points)} points, {self.slider.value} neurons")
    
    def save_points(self):
        filename = ctk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=os.getcwd(),
            initialfile=f"points_{int(datetime.now().timestamp())}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        print(filename)
    
    def load_points(self):
        filename = ctk.filedialog.askopenfilename(
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            initialdir=os.getcwd()
        )
        print(filename)