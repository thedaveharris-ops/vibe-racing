# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vibe Racing is a 2D Formula-style racing game prototype built with Python and tkinter. It features two-player local multiplayer with independent lap timing.

## Running the Application

```bash
python3 main.py
```

No dependencies beyond Python 3 standard library. No build step required.

## Architecture

Single-file application (`main.py`) with one `Game` class containing all functionality:

- **Initialization (lines 35-130)**: Canvas setup, car data structures, event binding, static track rendering
- **Game Loop (`_tick`)**: Runs at ~62.5 FPS with delta-time physics
- **Physics**: Velocity-based movement, friction, collision detection with rebound, off-track slowdown
- **Track Rendering (`_draw_static_track`)**: Figure-eight with loops, bridge/underpass, stands, pit wall
- **Lap Timing (`_check_lap`)**: Direction-aware finish line crossing with cooldown and minimum time validation
- **Input**: Two control schemes - Blue car (WASD), Yellow car (Arrow keys)

## Configuration Constants

All tunable values are at the top of `main.py` (lines 6-31):
- Display: 900x600 window, 70px track margin, 90px track width
- Physics: 340 max speed, 2.6 turn speed, 0.95 friction (0.72 off-track)
- Timing: 5-second countdown, 1.6-second flag display

## Car Data Structure

Each car is a dictionary with position (`x`, `y`), physics (`angle`, `vel`), lap tracking (`laps`, `last_lap_time`, `seen_right_side`, `lap_ready`), and visual properties (`fill`, `outline`, `wing`, `name`).

## Controls

| Action | Blue Car | Yellow Car |
|--------|----------|------------|
| Accelerate | W | Up Arrow |
| Brake | S | Down Arrow |
| Turn Left | A | Left Arrow |
| Turn Right | D | Right Arrow |
