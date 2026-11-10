import tkinter as tk
import math

class ColorSelector(tk.Frame):
    def __init__(self, parent, colors=("red", "blue")):
        super().__init__(parent, bg=parent["bg"])
        self.color = colors[0]
        self.circles = {}

        for c in colors:
            cv = tk.Canvas(self, width=50, height=50, bg=self["bg"],
                           highlightthickness=0)
            cv.pack(side="left", padx=10)
            circle_id = cv.create_oval(5, 5, 45, 45, fill=c,
                                       outline="black", width=1)
            cv.bind("<Button-1>", lambda event, c=c: self.select(c))
            self.circles[c] = (cv, circle_id)

        self.select(self.color)

    def select(self, color):
        self.color = color
        for c, (cv, circle_id) in self.circles.items():
            cv.itemconfig(circle_id, width=4 if c == color else 1)


class NeuronSlider(tk.Frame):
    """Label 'neurons : n' with a slider below it."""

    def __init__(self, parent, min_value=1, max_value=20, default=5):
        super().__init__(parent, bg=parent["bg"])
        self.text = tk.StringVar()

        self.label = tk.Label(self, textvariable=self.text, bg=self["bg"],
                              relief="groove", padx=12, pady=2)
        self.label.pack()

        self.scale = tk.Scale(self, from_=min_value, to=max_value,
                              orient="horizontal", showvalue=False,
                              length=170, bg=self["bg"],
                              highlightthickness=0, command=self._update)
        self.scale.pack()
        self.scale.set(default)

    def _update(self, value):
        self.text.set(f"neurons : {value}")

    @property
    def value(self):
        return self.scale.get()


class Spinner(tk.Canvas):
    """Loading indicator made of dots that fade around a circle."""

    def __init__(self, parent, size=50, dots=8):
        super().__init__(parent, width=size, height=size, bg=parent["bg"],
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
                                 fill="#dddddd", outline=""))

    def start(self):
        if not self.running:
            self.running = True
            self._animate()

    def stop(self):
        self.running = False
        for item in self.items:
            self.itemconfig(item, fill="#dddddd")

    def _animate(self):
        if not self.running:
            return
        for i, item in enumerate(self.items):
            age = (self.step - i) % self.dots
            level = min(225, 60 + age * 25)
            self.itemconfig(item, fill=f"#{level:02x}{level:02x}{level:02x}")
        self.step += 1
        self.after(100, self._animate)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZoNNe")
        self.geometry("1200x800")

        self.points = []   # list of (x, y, color)

        # Top area: drawing canvas
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=1,
                                highlightbackground="black")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.add_point)

        # Bottom area: control bar
        self.bar = tk.Frame(self, height=90, bg="#f0f0f0")
        self.bar.pack(side="bottom", fill="x")
        self.bar.pack_propagate(False)

        self.selector = ColorSelector(self.bar)
        self.selector.pack(side="left", padx=20)

        self.slider = NeuronSlider(self.bar)
        self.slider.pack(side="left", padx=30)

        self.spinner = Spinner(self.bar)
        self.spinner.pack(side="right", padx=20)

        self.start_button = tk.Button(self.bar, text="start", width=14,
                                      height=2, command=self.on_start)
        self.start_button.pack(side="right", padx=20)

    def add_point(self, event):
        color = self.selector.color
        r = 20
        self.canvas.create_oval(event.x - r, event.y - r,
                                event.x + r, event.y + r,
                                fill=color, outline="black")
        self.points.append((event.x, event.y, color))

    def on_start(self):
        if self.spinner.running:
            self.spinner.stop()
            self.start_button.config(text="start")
        else:
            self.spinner.start()
            self.start_button.config(text="stop")
            # TODO: train the neural network here with
            # self.points and self.slider.value neurons
            print(f"{len(self.points)} points, {self.slider.value} neurons")
