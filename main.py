import math
import time
import tkinter as tk


WINDOW_W = 900
WINDOW_H = 600
TRACK_MARGIN = 70
TRACK_WIDTH = 90
LOOP_RADIUS = 170
LOOP_OFFSET = 160
CENTER_X = WINDOW_W / 2
CENTER_Y = WINDOW_H / 2
BRIDGE_LEN = 240
UNDER_LEN = 220

# Track shape: lemniscate (figure-8)
# x = TRACK_SCALE_X * sin(t), y = TRACK_SCALE_Y * sin(t) * cos(t)
TRACK_SCALE_X = LOOP_OFFSET + LOOP_RADIUS * 0.7  # horizontal extent (~279)
TRACK_SCALE_Y = LOOP_RADIUS * 2.0  # vertical extent (~340)

# Finish line at bottom-right of track (t = π/4)
# At t=π/4: sin=0.707, cos=0.707, sin*cos=0.5
FINISH_X = CENTER_X + TRACK_SCALE_X * 0.707  # ~CENTER_X + 197
FINISH_Y = CENTER_Y + TRACK_SCALE_Y * 0.5    # ~CENTER_Y + 170
FINISH_Y0 = FINISH_Y - TRACK_WIDTH / 2
FINISH_Y1 = FINISH_Y + TRACK_WIDTH / 2
GRID_X = FINISH_X - 50
GRID_Y = FINISH_Y

CAR_LENGTH = 28
CAR_WIDTH = 14
CAR_SPEED = 340.0  # pixels per second
TURN_SPEED = 2.6   # radians per second
FRICTION = 0.95
COLLISION_DAMPING = 0.85
OFF_TRACK_FRICTION = 0.72
COUNTDOWN_SECONDS = 5
FLAG_SECONDS = 1.6


class Game:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.canvas = tk.Canvas(root, width=WINDOW_W, height=WINDOW_H, bg="#1b1f24", highlightthickness=0)
        self.canvas.pack()

        self.keys = set()
        self.last_time = time.perf_counter()
        self.race_start_time = self.last_time
        self.crowd_timer = 0.0
        self.crowd_phase = 0
        self.crowd_ids = []
        self.countdown_start = self.last_time
        self.race_active = False

        self.cars = [
            {
                "grid_dx": 0,
                "grid_dy": -16,
                "x": GRID_X,
                "y": GRID_Y - 16,
                "prev_x": GRID_X,
                "prev_y": GRID_Y - 16,
                "angle": 0.0,
                "vel": 0.0,
                "laps": 0,
                "last_lap_time": self.last_time,
                "last_lap_duration": None,
                "lap_cooldown": 0.0,
                "seen_right_side": False,
                "lap_ready": False,
                "on_overpass": True,  # Track which path car is on at crossing
                "controls": {"up": "w", "down": "s", "left": "a", "right": "d"},
                "fill": "#3fb8ff",
                "outline": "#102733",
                "wing": "#1c6a9e",
                "name": "Blue",
            },
            {
                "grid_dx": -26,
                "grid_dy": 16,
                "x": GRID_X - 26,
                "y": GRID_Y + 16,
                "prev_x": GRID_X - 26,
                "prev_y": GRID_Y + 16,
                "angle": 0.0,
                "vel": 0.0,
                "laps": 0,
                "last_lap_time": self.last_time,
                "last_lap_duration": None,
                "lap_cooldown": 0.0,
                "seen_right_side": False,
                "lap_ready": False,
                "on_overpass": True,  # Track which path car is on at crossing
                "controls": {"up": "up", "down": "down", "left": "left", "right": "right"},
                "fill": "#ffd166",
                "outline": "#3d2c0f",
                "wing": "#c5932f",
                "name": "Yellow",
            },
        ]

        self._bind_events()
        self._draw_static_track()
        self.car_ids = [self._draw_car(car) for car in self.cars]
        self.countdown_id = self.canvas.create_text(
            WINDOW_W / 2,
            WINDOW_H / 2,
            anchor="center",
            fill="#ffffff",
            font=("Helvetica", 72, "bold"),
            text=""
        )
        self.flag_ids = self._create_flag()
        self._show_flag(False)
        self.info_id = self.canvas.create_text(
            WINDOW_W - 10, 10,
            anchor="ne",
            fill="#9aa6b2",
            font=("Helvetica", 11),
            text="WASD (blue) and Arrow keys (yellow)"
        )
        self.reset_button = tk.Button(
            root, text="Reset Race", command=self._reset_race, bg="#30363d", fg="#e6edf3",
            activebackground="#3a4149", activeforeground="#ffffff", relief="flat", padx=8, pady=2
        )
        self.canvas.create_window(WINDOW_W - 80, 36, window=self.reset_button)
        self.hud_ids = [
            self.canvas.create_text(
                12, 12 + i * 18,
                anchor="nw",
                fill=car["fill"],
                font=("Helvetica", 11),
                text=""
            )
            for i, car in enumerate(self.cars)
        ]

        self._tick()

    def _bind_events(self) -> None:
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)

    def _on_key_press(self, event) -> None:
        self.keys.add(event.keysym.lower())

    def _on_key_release(self, event) -> None:
        self.keys.discard(event.keysym.lower())

    def _draw_static_track(self) -> None:
        self.canvas.delete("track")

        # Scenic background (stands, banners, infield)
        self.canvas.create_rectangle(0, 0, WINDOW_W, WINDOW_H, fill="#23402b", outline="", tags="track")
        self.canvas.create_rectangle(0, 0, WINDOW_W, TRACK_MARGIN - 12, fill="#20252b", outline="", tags="track")
        self.canvas.create_rectangle(0, WINDOW_H - (TRACK_MARGIN - 12), WINDOW_W, WINDOW_H,
                                     fill="#20252b", outline="", tags="track")
        stand_color = "#3b434c"
        seat_color = "#4b5661"
        self.crowd_ids = []
        for i in range(6):
            x0 = 40 + i * 140
            x1 = x0 + 90
            self.canvas.create_rectangle(x0, 6, x1, TRACK_MARGIN - 18, fill=stand_color, outline="", tags="track")
            self.canvas.create_line(x0 + 6, 16, x1 - 6, 16, fill=seat_color, width=2, tags="track")
            self.canvas.create_line(x0 + 8, 26, x1 - 8, 26, fill=seat_color, width=2, tags="track")
            self.canvas.create_line(x0 + 10, 36, x1 - 10, 36, fill=seat_color, width=2, tags="track")
            for r in range(3):
                for c in range(8):
                    cx = x0 + 10 + c * 10
                    cy = 12 + r * 10
                    color = "#7ad1ff" if (c + r) % 2 == 0 else "#f3a26b"
                    crowd = self.canvas.create_rectangle(
                        cx, cy, cx + 4, cy + 4, fill=color, outline="", tags="track"
                    )
                    self.crowd_ids.append(crowd)
        for i in range(5):
            bx0 = 70 + i * 170
            by0 = TRACK_MARGIN - 34
            self.canvas.create_rectangle(bx0, by0, bx0 + 80, by0 + 16, fill="#d35f4d", outline="", tags="track")
            self.canvas.create_text(bx0 + 40, by0 + 8, text="F1", fill="#1b1f24",
                                    font=("Helvetica", 9, "bold"), tags="track")

        # Figure-eight track as infinity symbol (lemniscate)
        # Parametric: x = TRACK_SCALE_X * sin(t), y = TRACK_SCALE_Y * sin(t) * cos(t)
        road_color = "#2a2f36"
        edge_color = "#3a4048"

        # Store scale values as instance variables for use in other methods
        self.track_scale_x = TRACK_SCALE_X
        self.track_scale_y = TRACK_SCALE_Y

        def lemniscate_point(t):
            """Return (x, y) on the lemniscate at parameter t"""
            x = CENTER_X + self.track_scale_x * math.sin(t)
            y = CENTER_Y + self.track_scale_y * math.sin(t) * math.cos(t)
            return (x, y)

        def get_track_points(t_start, t_end, num_points=80):
            """Get points along the lemniscate from t_start to t_end"""
            points = []
            for i in range(num_points + 1):
                t = t_start + (t_end - t_start) * i / num_points
                points.append(lemniscate_point(t))
            return points

        def flatten_points(points):
            """Flatten [(x,y), ...] to [x, y, x, y, ...]"""
            flat = []
            for x, y in points:
                flat.extend([x, y])
            return flat

        # The figure-8 crosses itself at center. We need to draw it so one path
        # goes over the other:
        # - OVERPASS: top-right (t~3π/4) → center → bottom-left (t~5π/4)
        # - UNDERPASS: bottom-right (t~π/4) → center → top-left (t~7π/4)
        #
        # Draw order: underpass path first, then overpass path on top

        # 1. Draw the UNDERPASS path (bottom-right ↔ top-left, passing through center at t=0)
        # This goes: t from ~5π/4 through 2π/0 to ~3π/4 (wrapping around)
        underpass_points = get_track_points(5 * math.pi / 4, 2 * math.pi + 3 * math.pi / 4)

        # Draw underpass: edge first, then road
        self.canvas.create_line(
            flatten_points(underpass_points),
            fill=edge_color, width=TRACK_WIDTH + 4, smooth=True,
            capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="track"
        )
        self.canvas.create_line(
            flatten_points(underpass_points),
            fill=road_color, width=TRACK_WIDTH, smooth=True,
            capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="track"
        )

        # 2. Draw shadow under the overpass
        shadow_offset = 6
        shadow_points = []
        for t_val in [math.pi - 0.5, math.pi - 0.25, math.pi, math.pi + 0.25, math.pi + 0.5]:
            px, py = lemniscate_point(t_val)
            shadow_points.append((px + shadow_offset, py + shadow_offset))
        self.canvas.create_line(
            flatten_points(shadow_points),
            fill="#0d0f12", width=TRACK_WIDTH + 10, smooth=True,
            capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="track"
        )

        # 3. Draw the OVERPASS path (top-right ↔ bottom-left, passing through center at t=π)
        # This goes: t from ~3π/4 through π to ~5π/4
        overpass_points = get_track_points(3 * math.pi / 4 - 0.3, 5 * math.pi / 4 + 0.3)

        # Draw overpass: just the road surface (underpass edges show through at the sides)
        self.canvas.create_line(
            flatten_points(overpass_points),
            fill=road_color, width=TRACK_WIDTH, smooth=True,
            capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="track"
        )

        # 4. Center dashed line - draw carefully to hide underpass line under overpass
        # Underpass dashed line in TWO parts (small gap at crossing zone around t=0)
        # Part 1: from bottom-left (5π/4) to just before crossing
        self.canvas.create_line(
            flatten_points(get_track_points(5 * math.pi / 4, 2 * math.pi - 0.12, num_points=50)),
            fill="#ffffff", width=2, dash=(15, 15), smooth=True, tags="track"
        )
        # Part 2: from just after crossing to top-right (3π/4)
        self.canvas.create_line(
            flatten_points(get_track_points(0.12, 3 * math.pi / 4, num_points=50)),
            fill="#ffffff", width=2, dash=(15, 15), smooth=True, tags="track"
        )
        # Overpass dashed line (drawn on top, covers the crossing)
        self.canvas.create_line(
            flatten_points(get_track_points(3 * math.pi / 4 - 0.3, 5 * math.pi / 4 + 0.3, num_points=40)),
            fill="#ffffff", width=2, dash=(15, 15), smooth=True, tags="track"
        )


        # Finish line (bottom straight, vertical checker)
        finish_x = FINISH_X
        finish_y0 = FINISH_Y0
        finish_y1 = FINISH_Y1
        block_h = 10
        for i, y in enumerate(range(int(finish_y0), int(finish_y1), block_h)):
            color = "#f2f2f2" if i % 2 == 0 else "#1b1f24"
            self.canvas.create_rectangle(
                finish_x - 6, y, finish_x + 6, min(y + block_h, finish_y1),
                fill=color, outline="", tags="track"
            )
        self.finish_line = {
            "x": finish_x,
            "y0": finish_y0,
            "y1": finish_y1,
        }
        # Starting grid to the left of the finish line
        grid_w = 28
        grid_h = 18
        for i in range(2):
            gx = GRID_X - (i * 26)
            gy = GRID_Y - 24 + (i * 32)
            self.canvas.create_rectangle(
                gx - grid_w / 2, gy - grid_h / 2, gx + grid_w / 2, gy + grid_h / 2,
                outline="#5f6b75", width=2, tags="track"
            )

        self.canvas.tag_raise("track")

    def _create_flag(self):
        cx = WINDOW_W / 2
        cy = WINDOW_H / 2
        w = 120
        h = 80
        block = 20
        ids = []
        for r in range(0, h, block):
            for c in range(0, w, block):
                color = "#ffffff" if (r // block + c // block) % 2 == 0 else "#1b1f24"
                x0 = cx - w / 2 + c
                y0 = cy - h / 2 + r
                rect = self.canvas.create_rectangle(x0, y0, x0 + block, y0 + block,
                                                    fill=color, outline="", tags="flag")
                ids.append(rect)
        pole = self.canvas.create_line(cx - w / 2 - 10, cy - h / 2, cx - w / 2 - 10, cy + h / 2,
                                       fill="#cfd4da", width=4, tags="flag")
        ids.append(pole)
        return ids

    def _show_flag(self, show: bool) -> None:
        state = "normal" if show else "hidden"
        for flag_id in self.flag_ids:
            self.canvas.itemconfig(flag_id, state=state)

    def _draw_car(self, car):
        shapes = self._car_shape_points(car)
        body_id = self.canvas.create_polygon(
            shapes["body"], fill=car["fill"], outline=car["outline"], width=2, tags="car"
        )
        nose_id = self.canvas.create_polygon(
            shapes["nose"], fill=car["fill"], outline=car["outline"], width=2, tags="car"
        )
        rear_id = self.canvas.create_polygon(
            shapes["rear_wing"], fill=car["wing"], outline=car["outline"], width=1, tags="car"
        )
        front_id = self.canvas.create_polygon(
            shapes["front_wing"], fill=car["wing"], outline=car["outline"], width=1, tags="car"
        )
        return {"body": body_id, "nose": nose_id, "rear_wing": rear_id, "front_wing": front_id}

    def _car_shape_points(self, car):
        # Car centered at origin then rotated around (0,0) and translated
        half_l = CAR_LENGTH / 2
        half_w = CAR_WIDTH / 2

        body = [
            (-half_l * 0.8, -half_w * 0.6),
            (half_l * 0.2, -half_w * 0.45),
            (half_l * 0.6, -half_w * 0.25),
            (half_l * 0.85, 0),
            (half_l * 0.6, half_w * 0.25),
            (half_l * 0.2, half_w * 0.45),
            (-half_l * 0.8, half_w * 0.6),
            (-half_l * 1.0, half_w * 0.4),
            (-half_l * 1.0, -half_w * 0.4),
        ]

        nose = [
            (half_l * 0.6, -half_w * 0.22),
            (half_l * 1.15, 0),
            (half_l * 0.6, half_w * 0.22),
        ]

        rear_wing = [
            (-half_l * 1.2, -half_w * 0.8),
            (-half_l * 0.7, -half_w * 0.8),
            (-half_l * 0.7, half_w * 0.8),
            (-half_l * 1.2, half_w * 0.8),
        ]

        front_wing = [
            (half_l * 0.9, -half_w * 0.65),
            (half_l * 1.25, -half_w * 0.65),
            (half_l * 1.25, half_w * 0.65),
            (half_l * 0.9, half_w * 0.65),
        ]

        return {
            "body": self._transform_points(body, car),
            "nose": self._transform_points(nose, car),
            "rear_wing": self._transform_points(rear_wing, car),
            "front_wing": self._transform_points(front_wing, car),
        }

    def _transform_points(self, pts, car):
        sin_a = math.sin(car["angle"])
        cos_a = math.cos(car["angle"])

        out = []
        for x, y in pts:
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            out.extend([car["x"] + rx, car["y"] + ry])
        return out

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now

        self._update_start_sequence(now)

        for car in self.cars:
            car["prev_x"] = car["x"]
            car["prev_y"] = car["y"]

            if self.race_active:
                controls = car["controls"]
                if controls["up"] in self.keys:
                    car["vel"] += CAR_SPEED * dt
                if controls["down"] in self.keys:
                    car["vel"] -= CAR_SPEED * dt

                if controls["left"] in self.keys:
                    car["angle"] -= TURN_SPEED * dt
                if controls["right"] in self.keys:
                    car["angle"] += TURN_SPEED * dt

                car["vel"] *= FRICTION

                car["x"] += math.cos(car["angle"]) * car["vel"] * dt
                car["y"] += math.sin(car["angle"]) * car["vel"] * dt

                if self._is_off_track(car):
                    car["vel"] *= OFF_TRACK_FRICTION

                self._clamp_to_track(car)
                self._check_lap(car, now, dt)
            else:
                car["vel"] = 0.0

            # Update which path (overpass/underpass) the car is on
            self._update_car_path(car)

        self._resolve_collisions()

        for idx, car in enumerate(self.cars):
            shapes = self._car_shape_points(car)
            ids = self.car_ids[idx]
            self._set_car_visibility(ids, not self._should_hide_car(car))
            self.canvas.coords(ids["body"], *shapes["body"])
            self.canvas.coords(ids["nose"], *shapes["nose"])
            self.canvas.coords(ids["rear_wing"], *shapes["rear_wing"])
            self.canvas.coords(ids["front_wing"], *shapes["front_wing"])

        self._update_hud(now)
        self._animate_crowd(dt)
        self.root.after(16, self._tick)

    def _update_start_sequence(self, now: float) -> None:
        elapsed = now - self.countdown_start
        if elapsed < COUNTDOWN_SECONDS:
            count = COUNTDOWN_SECONDS - int(elapsed)
            self.canvas.itemconfig(self.countdown_id, text=str(count), state="normal")
            self._show_flag(False)
            return

        self.canvas.itemconfig(self.countdown_id, text="", state="hidden")
        if not self.race_active:
            self.race_active = True
            for car in self.cars:
                car["last_lap_time"] = now
                car["last_lap_duration"] = None
                car["lap_cooldown"] = 0.0
                car["seen_right_side"] = False
                car["lap_ready"] = False

        if elapsed < COUNTDOWN_SECONDS + FLAG_SECONDS:
            self._show_flag(True)
            self._wave_flag(elapsed - COUNTDOWN_SECONDS)
        else:
            self._show_flag(False)

    def _wave_flag(self, phase_time: float) -> None:
        phase = int(phase_time * 6) % 2
        for idx, flag_id in enumerate(self.flag_ids):
            if idx % 3 == phase:
                self.canvas.itemconfig(flag_id, fill="#ffffff")
            elif idx % 3 == (phase + 1) % 2:
                self.canvas.itemconfig(flag_id, fill="#1b1f24")

    def _set_car_visibility(self, ids, visible: bool) -> None:
        state = "normal" if visible else "hidden"
        self.canvas.itemconfig(ids["body"], state=state)
        self.canvas.itemconfig(ids["nose"], state=state)
        self.canvas.itemconfig(ids["rear_wing"], state=state)
        self.canvas.itemconfig(ids["front_wing"], state=state)

    def _update_car_path(self, car) -> None:
        """Update which path (overpass/underpass) the car is on based on quadrant.

        OVERPASS: top-right quadrant OR bottom-left quadrant
        UNDERPASS: top-left quadrant OR bottom-right quadrant

        Only update when car is NOT near the center crossing.
        """
        x, y = car["x"], car["y"]

        # Only update when not near the crossing (to avoid flickering)
        crossing_radius = TRACK_WIDTH * 1.5
        if abs(x - CENTER_X) < crossing_radius and abs(y - CENTER_Y) < crossing_radius:
            return  # Keep current path assignment when near crossing

        # Determine quadrant relative to center
        in_right = x > CENTER_X
        in_top = y < CENTER_Y  # Screen coords: y increases downward

        # OVERPASS path: top-right OR bottom-left
        # UNDERPASS path: top-left OR bottom-right
        if (in_right and in_top) or (not in_right and not in_top):
            car["on_overpass"] = True
        else:
            car["on_overpass"] = False

    def _is_near_crossing(self, x: float, y: float) -> bool:
        """Check if position is near the center crossing"""
        crossing_radius = TRACK_WIDTH * 1.0
        return abs(x - CENTER_X) < crossing_radius and abs(y - CENTER_Y) < crossing_radius

    def _should_hide_car(self, car) -> bool:
        """Determine if car should be hidden (under the overpass)"""
        if not self._is_near_crossing(car["x"], car["y"]):
            return False  # Only hide near the crossing

        # Hide if on underpass path (not on overpass)
        return not car["on_overpass"]

    def _animate_crowd(self, dt: float) -> None:
        self.crowd_timer += dt
        if self.crowd_timer < 0.25:
            return
        self.crowd_timer = 0.0
        self.crowd_phase = (self.crowd_phase + 1) % 2
        for idx, crowd_id in enumerate(self.crowd_ids):
            if (idx + self.crowd_phase) % 3 == 0:
                color = "#f3a26b"
            elif (idx + self.crowd_phase) % 3 == 1:
                color = "#7ad1ff"
            else:
                color = "#e8e4b3"
            self.canvas.itemconfig(crowd_id, fill=color)

    def _update_hud(self, now: float) -> None:
        for idx, car in enumerate(self.cars):
            current_lap = 0.0 if not self.race_active else now - car["last_lap_time"]
            last_lap = car["last_lap_duration"]
            last_text = f"{last_lap:.2f}s" if last_lap is not None else "--"
            text = f"{car['name']}: Laps {car['laps']} | Lap {current_lap:.2f}s | Last {last_text}"
            self.canvas.itemconfig(self.hud_ids[idx], text=text)

    def _reset_race(self) -> None:
        now = time.perf_counter()
        self.last_time = now
        self.race_start_time = now
        self.countdown_start = now
        self.race_active = False
        self.canvas.itemconfig(self.countdown_id, text="", state="hidden")
        self._show_flag(False)
        for car in self.cars:
            car["x"] = GRID_X + car["grid_dx"]
            car["y"] = GRID_Y + car["grid_dy"]
            car["prev_x"] = car["x"]
            car["prev_y"] = car["y"]
            car["angle"] = 0.0
            car["vel"] = 0.0
            car["laps"] = 0
            car["last_lap_time"] = now
            car["last_lap_duration"] = None
            car["lap_cooldown"] = 0.0
            car["seen_right_side"] = False
            car["lap_ready"] = False
            car["on_overpass"] = True
        for ids in self.car_ids:
            self._set_car_visibility(ids, True)

    def _check_lap(self, car, now: float, dt: float) -> None:
        if car["lap_cooldown"] > 0.0:
            car["lap_cooldown"] = max(0.0, car["lap_cooldown"] - dt)

        x0 = car["prev_x"]
        x1 = car["x"]
        if x0 == x1:
            return

        line_x = self.finish_line["x"]
        y0 = self.finish_line["y0"]
        y1 = self.finish_line["y1"]

        if car["x"] > line_x + 8:
            car["seen_right_side"] = True
        if car["x"] < line_x - 8 and car["seen_right_side"]:
            car["lap_ready"] = True

        # Anticlockwise: cross the finish line moving left-to-right on the bottom straight.
        crossed = x0 < line_x <= x1
        in_strip = False
        if crossed and x0 != x1:
            t = (line_x - x0) / (x1 - x0)
            y_at = car["prev_y"] + t * (car["y"] - car["prev_y"])
            in_strip = y0 <= y_at <= y1

        if crossed and in_strip and car["lap_ready"] and car["lap_cooldown"] <= 0.0:
            lap_time = now - car["last_lap_time"]
            if lap_time > 0.6:
                car["laps"] += 1
                car["last_lap_duration"] = lap_time
                car["last_lap_time"] = now
                car["lap_cooldown"] = 1.2
                car["seen_right_side"] = False
                car["lap_ready"] = False

    def _resolve_collisions(self) -> None:
        if len(self.cars) < 2:
            return

        car_a = self.cars[0]
        car_b = self.cars[1]

        dx = car_b["x"] - car_a["x"]
        dy = car_b["y"] - car_a["y"]
        dist = math.hypot(dx, dy)
        min_dist = (CAR_LENGTH * 0.75)

        if dist == 0.0:
            return

        if dist < min_dist:
            overlap = min_dist - dist
            nx = dx / dist
            ny = dy / dist

            car_a["x"] -= nx * overlap * 0.5
            car_a["y"] -= ny * overlap * 0.5
            car_b["x"] += nx * overlap * 0.5
            car_b["y"] += ny * overlap * 0.5

            car_a["vel"] *= -COLLISION_DAMPING
            car_b["vel"] *= -COLLISION_DAMPING

            self._clamp_to_track(car_a)
            self._clamp_to_track(car_b)

    def _is_off_track(self, car) -> bool:
        return not self._is_on_track(car["x"], car["y"])

    def _is_on_track(self, x: float, y: float) -> bool:
        """Check if point is on the lemniscate track"""
        half_w = TRACK_WIDTH / 2

        # Find minimum distance to the lemniscate curve by sampling
        min_dist = float('inf')
        for i in range(64):
            t = 2 * math.pi * i / 64
            curve_x = CENTER_X + TRACK_SCALE_X * math.sin(t)
            curve_y = CENTER_Y + TRACK_SCALE_Y * math.sin(t) * math.cos(t)
            dist = math.hypot(x - curve_x, y - curve_y)
            min_dist = min(min_dist, dist)

        return min_dist <= half_w

    def _clamp_to_track(self, car) -> None:
        # Keep the car on-screen; off-track is handled by friction.
        outer_min_x = CAR_WIDTH
        outer_min_y = CAR_WIDTH
        outer_max_x = WINDOW_W - CAR_WIDTH
        outer_max_y = WINDOW_H - CAR_WIDTH

        car["x"] = max(outer_min_x, min(outer_max_x, car["x"]))
        car["y"] = max(outer_min_y, min(outer_max_y, car["y"]))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Vibe Racing - Prototype")
    root.resizable(False, False)
    Game(root)
    root.mainloop()
