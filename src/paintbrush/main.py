#!/usr/bin/env python3
"""
PaintBrush - Enhanced mid-level drawing application
Modern GTK4/Adwaita application with Cairo graphics
Version 1.4.0 with layers, crop, rotate, resize, brush shapes, gradient, clipboard, recent files
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gdk, GdkPixbuf, Gio, GLib, GObject, Pango
import cairo
import math
import os
import sys
import locale
import gettext
import json
import random
import struct
from pathlib import Path

# Internationalization setup
GETTEXT_DOMAIN = 'paintbrush'
LOCALE_DIR = '/usr/share/locale'
DEV_LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'po')

# Try to set up locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

# Auto-detect system language and load translations
_lang = None
try:
    _lang_tuple = locale.getlocale()
    if _lang_tuple and _lang_tuple[0]:
        _lang = _lang_tuple[0]
except Exception:
    pass

# Set up gettext — try dev directory first, then system
for _ldir in [DEV_LOCALE_DIR, LOCALE_DIR]:
    if os.path.isdir(_ldir):
        gettext.bindtextdomain(GETTEXT_DOMAIN, _ldir)
gettext.textdomain(GETTEXT_DOMAIN)
_ = gettext.gettext

# Config directory for settings
CONFIG_DIR = Path(GLib.get_user_config_dir()) / "paintbrush"

# Default settings
DEFAULT_SETTINGS = {
    "canvas_width": 800,
    "canvas_height": 600,
    "background_color": "white",
    "auto_save_interval": 0,
    "undo_history_limit": 50,
    "default_save_format": "png",
    "antialiasing": True,
    "brush_interpolation": "good",
    "last_open_dir": "",
    "last_save_dir": "",
    "welcome_shown": False,
    "grid_size": 20,
    "snap_to_grid": False,
    "recent_files": [],
}

# 48-color default palette (6 rows x 8 columns)
DEFAULT_PALETTE = [
    # Row 1: Pure colors
    (0.0, 0.0, 0.0), (0.33, 0.33, 0.33), (0.5, 0.5, 0.5), (0.67, 0.67, 0.67),
    (0.83, 0.83, 0.83), (1.0, 1.0, 1.0), (1.0, 0.0, 0.0), (0.0, 0.5, 0.0),
    # Row 2: Blues and purples
    (0.0, 0.0, 1.0), (0.0, 0.0, 0.55), (0.29, 0.0, 0.51), (0.5, 0.0, 0.5),
    (0.55, 0.0, 0.55), (0.73, 0.33, 0.83), (0.87, 0.63, 0.87), (0.94, 0.9, 0.95),
    # Row 3: Greens and teals
    (0.0, 1.0, 0.0), (0.0, 0.8, 0.0), (0.0, 0.55, 0.0), (0.13, 0.55, 0.13),
    (0.0, 0.5, 0.5), (0.0, 0.81, 0.82), (0.56, 0.93, 0.56), (0.6, 0.98, 0.6),
    # Row 4: Yellows and oranges
    (1.0, 1.0, 0.0), (1.0, 0.84, 0.0), (1.0, 0.65, 0.0), (1.0, 0.55, 0.0),
    (1.0, 0.39, 0.28), (1.0, 0.27, 0.0), (0.8, 0.52, 0.25), (0.55, 0.27, 0.07),
    # Row 5: Reds and pinks
    (1.0, 0.0, 0.0), (0.86, 0.08, 0.24), (0.8, 0.0, 0.0), (0.55, 0.0, 0.0),
    (1.0, 0.41, 0.71), (1.0, 0.71, 0.76), (1.0, 0.08, 0.58), (0.78, 0.08, 0.52),
    # Row 6: Skin tones and earth
    (1.0, 0.87, 0.75), (1.0, 0.81, 0.66), (0.96, 0.72, 0.53), (0.87, 0.63, 0.44),
    (0.78, 0.55, 0.37), (0.63, 0.42, 0.27), (0.44, 0.26, 0.13), (0.29, 0.15, 0.07),
]

# Supported file formats
OPEN_FORMATS = {
    "png": ("PNG", ["image/png"], [".png"]),
    "jpeg": ("JPEG", ["image/jpeg"], [".jpg", ".jpeg"]),
    "bmp": ("BMP", ["image/bmp"], [".bmp"]),
    "gif": ("GIF", ["image/gif"], [".gif"]),
    "tiff": ("TIFF", ["image/tiff"], [".tif", ".tiff"]),
    "svg": ("SVG", ["image/svg+xml"], [".svg"]),
    "ico": ("ICO", ["image/x-icon", "image/vnd.microsoft.icon"], [".ico"]),
    "tga": ("TGA", ["image/x-tga"], [".tga"]),
    "pnm": ("PNM", ["image/x-portable-anymap"], [".pnm", ".pbm", ".pgm", ".ppm"]),
    "xpm": ("XPM", ["image/x-xpixmap"], [".xpm"]),
    "xbm": ("XBM", ["image/x-xbitmap"], [".xbm"]),
    "webp": ("WebP", ["image/webp"], [".webp"]),
}

SAVE_FORMATS = {
    "png": ("PNG", ".png", "image/png"),
    "jpeg": ("JPEG", ".jpg", "image/jpeg"),
    "bmp": ("BMP", ".bmp", "image/bmp"),
    "tiff": ("TIFF", ".tif", "image/tiff"),
    "ico": ("ICO", ".ico", "image/x-icon"),
    "webp": ("WebP", ".webp", "image/webp"),
}


def _load_settings():
    path = CONFIG_DIR / "settings.json"
    settings = dict(DEFAULT_SETTINGS)
    if path.exists():
        try:
            saved = json.loads(path.read_text())
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def _save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "settings.json").write_text(
        json.dumps(settings, indent=2, ensure_ascii=False))


class UndoRedoManager:
    """Manages undo/redo operations for the canvas"""

    def __init__(self, max_history=50):
        self.max_history = max_history
        self.history = []
        self.current_index = -1

    def save_state(self, surface):
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]

        surface_copy = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                          surface.get_width(),
                                          surface.get_height())
        ctx = cairo.Context(surface_copy)
        ctx.set_source_surface(surface, 0, 0)
        ctx.paint()

        self.history.append(surface_copy)
        self.current_index += 1

        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1

    def can_undo(self):
        return self.current_index > 0

    def can_redo(self):
        return self.current_index < len(self.history) - 1

    def undo(self):
        if self.can_undo():
            self.current_index -= 1
            return self.history[self.current_index]
        return None

    def redo(self):
        if self.can_redo():
            self.current_index += 1
            return self.history[self.current_index]
        return None


class DrawingArea(Gtk.DrawingArea):
    """Enhanced drawing area with advanced tools and features"""

    def __init__(self, settings):
        super().__init__()

        self.settings = settings

        # Canvas properties
        self.width = settings.get("canvas_width", 800)
        self.height = settings.get("canvas_height", 600)
        self.surface = None
        self.ctx = None
        self.zoom_level = 1.0

        # Drawing state
        self.drawing = False
        self.last_x = 0
        self.last_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Tool properties
        self.tool = "brush"
        self.brush_size = 5
        self.fg_color = (0.0, 0.0, 0.0, 1.0)  # RGBA foreground
        self.bg_color = (1.0, 1.0, 1.0, 1.0)  # RGBA background
        self.line_width = 2
        self.brush_opacity = 1.0

        # Tool-specific properties
        self.fill_tolerance = 10
        self.polygon_points = []
        self.text_content = ""
        self.font_size = 16

        # Layers
        self.layers = []  # list of {"name": str, "surface": cairo.ImageSurface, "visible": bool}
        self.active_layer_index = 0

        # Brush shape: "round", "square", "calligraphy"
        self.brush_shape = "round"

        # Stroke width for shape tools (separate from brush_size)
        self.stroke_width = 2
        # Shape fill mode: "outline" or "filled"
        self.shape_fill_mode = "outline"

        # Crop tool state
        self.crop_rect = None  # (x, y, w, h) for pending crop

        # Gradient mode: "linear" or "radial"
        self.gradient_mode = "linear"

        # Grid
        self.show_grid = False
        self.grid_size = settings.get("grid_size", 20)
        self.snap_to_grid = settings.get("snap_to_grid", False)

        # Selection state
        self.selection = None  # (x, y, w, h) or None
        self.selection_surface = None
        self.selection_dragging = False
        self.selection_offset_x = 0
        self.selection_offset_y = 0

        # Preview surface for shape drawing
        self.preview_surface = None

        # Cursor position tracking
        self.cursor_x = 0
        self.cursor_y = 0

        # Recent colors
        self.recent_colors = []

        # Undo/Redo
        undo_limit = settings.get("undo_history_limit", 50)
        self.undo_manager = UndoRedoManager(max_history=undo_limit)

        # Antialiasing
        self.use_antialiasing = settings.get("antialiasing", True)

        # Callback for status updates
        self.on_status_update = None

        # Setup drawing area
        self.set_size_request(self.width, self.height)
        self.set_draw_func(self.on_draw)

        # Mouse/touch events
        self.gesture_click = Gtk.GestureClick()
        self.gesture_drag = Gtk.GestureDrag()

        self.gesture_click.connect("pressed", self.on_button_press)
        self.gesture_click.connect("released", self.on_button_release)
        self.gesture_drag.connect("drag-update", self.on_motion_notify)
        self.gesture_drag.connect("drag-begin", self.on_drag_begin)
        self.gesture_drag.connect("drag-end", self.on_drag_end)

        self.add_controller(self.gesture_click)
        self.add_controller(self.gesture_drag)

        # Motion controller for cursor tracking
        self.motion_ctrl = Gtk.EventControllerMotion()
        self.motion_ctrl.connect("motion", self.on_pointer_motion)
        self.add_controller(self.motion_ctrl)

        # Initialize canvas
        self.initialize_surface()

    def initialize_surface(self):
        """Initialize the drawing surface with a base layer"""
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)

        # Fill with background color
        bg = self.settings.get("background_color", "white")
        if bg == "transparent":
            self.ctx.set_source_rgba(0, 0, 0, 0)
        else:
            self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

        # Initialize layers
        self.layers = [{"name": _("Background"), "surface": self.surface, "visible": True}]
        self.active_layer_index = 0

        self.set_size_request(self.width, self.height)
        self.undo_manager.save_state(self.surface)

    def _apply_antialiasing(self, ctx):
        if self.use_antialiasing:
            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
        else:
            ctx.set_antialias(cairo.ANTIALIAS_NONE)

    def snap(self, x, y):
        """Snap coordinates to grid if enabled"""
        if self.snap_to_grid and self.show_grid:
            gs = self.grid_size
            x = round(x / gs) * gs
            y = round(y / gs) * gs
        return x, y

    def on_draw(self, area, ctx, width, height, user_data=None):
        """Draw callback - composite all layers to screen with zoom"""
        ctx.scale(self.zoom_level, self.zoom_level)

        # Composite all visible layers
        for layer in self.layers:
            if layer["visible"]:
                ctx.set_source_surface(layer["surface"], 0, 0)
                ctx.paint()

        # Draw preview surface (for shape previews)
        if self.preview_surface:
            ctx.set_source_surface(self.preview_surface, 0, 0)
            ctx.paint()

        # Draw grid overlay
        if self.show_grid:
            self._draw_grid(ctx)

        # Draw crop rectangle
        if self.crop_rect:
            cx, cy, cw, ch = self.crop_rect
            # Dim outside crop area
            ctx.set_source_rgba(0, 0, 0, 0.4)
            ctx.rectangle(0, 0, self.width, cy)
            ctx.fill()
            ctx.rectangle(0, cy + ch, self.width, self.height - cy - ch)
            ctx.fill()
            ctx.rectangle(0, cy, cx, ch)
            ctx.fill()
            ctx.rectangle(cx + cw, cy, self.width - cx - cw, ch)
            ctx.fill()
            # Crop border
            ctx.set_dash([4, 4])
            ctx.set_source_rgba(1, 1, 1, 0.9)
            ctx.set_line_width(1)
            ctx.rectangle(cx, cy, cw, ch)
            ctx.stroke()
            ctx.set_dash([])

        # Draw selection rectangle
        if self.selection:
            sx, sy, sw, sh = self.selection
            ctx.set_dash([4, 4])
            ctx.set_source_rgba(0, 0, 0, 0.8)
            ctx.set_line_width(1)
            ctx.rectangle(sx, sy, sw, sh)
            ctx.stroke()
            ctx.set_dash([4, 4], 4)
            ctx.set_source_rgba(1, 1, 1, 0.8)
            ctx.rectangle(sx, sy, sw, sh)
            ctx.stroke()
            ctx.set_dash([])

            # Draw selection content if being moved
            if self.selection_surface:
                ctx.set_source_surface(self.selection_surface, sx, sy)
                ctx.paint()

    def _draw_grid(self, ctx):
        """Draw grid overlay"""
        ctx.set_source_rgba(0.5, 0.5, 0.5, 0.3)
        ctx.set_line_width(0.5)
        gs = self.grid_size
        for x in range(0, self.width + 1, gs):
            ctx.move_to(x, 0)
            ctx.line_to(x, self.height)
        for y in range(0, self.height + 1, gs):
            ctx.move_to(0, y)
            ctx.line_to(self.width, y)
        ctx.stroke()

    def save_state_for_undo(self):
        self.undo_manager.save_state(self.surface)

    def undo(self):
        previous_surface = self.undo_manager.undo()
        if previous_surface:
            self.ctx.set_operator(cairo.OPERATOR_SOURCE)
            self.ctx.set_source_surface(previous_surface, 0, 0)
            self.ctx.paint()
            self.ctx.set_operator(cairo.OPERATOR_OVER)
            self.queue_draw()
            return True
        return False

    def redo(self):
        next_surface = self.undo_manager.redo()
        if next_surface:
            self.ctx.set_operator(cairo.OPERATOR_SOURCE)
            self.ctx.set_source_surface(next_surface, 0, 0)
            self.ctx.paint()
            self.ctx.set_operator(cairo.OPERATOR_OVER)
            self.queue_draw()
            return True
        return False

    def zoom_in(self):
        self.zoom_level = min(4.0, self.zoom_level * 1.25)
        self.queue_draw()

    def zoom_out(self):
        self.zoom_level = max(0.25, self.zoom_level / 1.25)
        self.queue_draw()

    def zoom_reset(self):
        self.zoom_level = 1.0
        self.queue_draw()

    def on_pointer_motion(self, controller, x, y):
        """Track cursor position for status bar"""
        self.cursor_x = x / self.zoom_level
        self.cursor_y = y / self.zoom_level
        if self.on_status_update:
            self.on_status_update()

    def on_drag_begin(self, gesture, start_x, start_y):
        """Start drawing operation"""
        start_x /= self.zoom_level
        start_y /= self.zoom_level
        start_x, start_y = self.snap(start_x, start_y)

        self.drawing = True
        self.last_x = start_x
        self.last_y = start_y
        self.drag_start_x = start_x
        self.drag_start_y = start_y

        if self.tool in ["brush", "eraser", "spray"]:
            self.save_state_for_undo()

        if self.tool == "crop":
            # Start crop rectangle
            return

        if self.tool == "brush":
            self.draw_dot(start_x, start_y)
        elif self.tool == "eraser":
            self.erase_dot(start_x, start_y)
        elif self.tool == "spray":
            self.save_state_for_undo()
            self.spray_paint(start_x, start_y)
        elif self.tool == "fill":
            self.save_state_for_undo()
            self.flood_fill(int(start_x), int(start_y))
        elif self.tool == "polygon":
            self.polygon_points.append((start_x, start_y))
        elif self.tool == "text":
            self.save_state_for_undo()
            self.draw_text(start_x, start_y)
        elif self.tool == "eyedropper":
            self.pick_color(int(start_x), int(start_y))
        elif self.tool == "select":
            # Check if clicking inside existing selection to move it
            if self.selection:
                sx, sy, sw, sh = self.selection
                if sx <= start_x <= sx + sw and sy <= start_y <= sy + sh:
                    self.selection_dragging = True
                    self.selection_offset_x = start_x - sx
                    self.selection_offset_y = start_y - sy
                    return
            self.selection = None
            self.selection_surface = None
            self.selection_dragging = False

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Handle drag end for shape tools"""
        if not self.drawing:
            return

        end_x = self.drag_start_x + offset_x / self.zoom_level
        end_y = self.drag_start_y + offset_y / self.zoom_level
        end_x, end_y = self.snap(end_x, end_y)

        self.drawing = False
        self.preview_surface = None

        if self.tool == "crop":
            self.start_crop(self.drag_start_x, self.drag_start_y, end_x, end_y)
            self.drawing = False
            return

        if self.tool == "gradient":
            self.draw_gradient(self.drag_start_x, self.drag_start_y, end_x, end_y)
            self.drawing = False
            return

        if self.tool in ["line", "rectangle", "circle", "star", "arrow", "rounded_rectangle"]:
            self.save_state_for_undo()

        if self.tool == "line":
            self.draw_line(self.drag_start_x, self.drag_start_y, end_x, end_y)
        elif self.tool == "rectangle":
            self.draw_rectangle(self.drag_start_x, self.drag_start_y, end_x, end_y)
        elif self.tool == "circle":
            self.draw_circle(self.drag_start_x, self.drag_start_y, end_x, end_y)
        elif self.tool == "star":
            self.draw_star(self.drag_start_x, self.drag_start_y, end_x, end_y)
        elif self.tool == "arrow":
            self.draw_arrow(self.drag_start_x, self.drag_start_y, end_x, end_y)
        elif self.tool == "rounded_rectangle":
            self.draw_rounded_rectangle(self.drag_start_x, self.drag_start_y, end_x, end_y)
        elif self.tool == "select":
            if not self.selection_dragging:
                x1, y1 = self.drag_start_x, self.drag_start_y
                x2, y2 = end_x, end_y
                sx = min(x1, x2)
                sy = min(y1, y2)
                sw = abs(x2 - x1)
                sh = abs(y2 - y1)
                if sw > 2 and sh > 2:
                    self.selection = (sx, sy, sw, sh)
            else:
                self.selection_dragging = False

        self.queue_draw()

    def on_button_press(self, gesture, n_press, x, y):
        """Handle button press for single-click tools"""
        x /= self.zoom_level
        y /= self.zoom_level

        if self.tool in ["brush", "eraser", "fill", "text", "spray", "eyedropper", "select", "crop", "gradient"]:
            return

        if self.tool == "polygon" and n_press == 2:
            if len(self.polygon_points) > 2:
                self.save_state_for_undo()
                self.draw_polygon()
                self.polygon_points = []
            return

        self.last_x = x
        self.last_y = y
        self.drawing = True

    def on_button_release(self, gesture, n_press, x, y):
        """Handle button release"""
        pass  # Shape finalization moved to on_drag_end

    def on_motion_notify(self, gesture, offset_x, offset_y):
        """Handle mouse/touch drag"""
        if not self.drawing:
            return

        current_x = self.drag_start_x + (offset_x / self.zoom_level)
        current_y = self.drag_start_y + (offset_y / self.zoom_level)
        current_x, current_y = self.snap(current_x, current_y)

        if self.tool == "brush":
            self.draw_line_segment(self.last_x, self.last_y, current_x, current_y)
            self.last_x = current_x
            self.last_y = current_y
        elif self.tool == "eraser":
            self.erase_line_segment(self.last_x, self.last_y, current_x, current_y)
            self.last_x = current_x
            self.last_y = current_y
        elif self.tool == "spray":
            self.spray_paint(current_x, current_y)
        elif self.tool == "select" and self.selection_dragging and self.selection:
            sx, sy, sw, sh = self.selection
            new_x = current_x - self.selection_offset_x
            new_y = current_y - self.selection_offset_y
            self.selection = (new_x, new_y, sw, sh)
        elif self.tool == "crop":
            # Show crop preview
            sx = min(self.drag_start_x, current_x)
            sy = min(self.drag_start_y, current_y)
            sw = abs(current_x - self.drag_start_x)
            sh = abs(current_y - self.drag_start_y)
            if sw > 2 and sh > 2:
                self.crop_rect = (sx, sy, sw, sh)
        elif self.tool == "gradient":
            # Show gradient preview
            self._update_gradient_preview(self.drag_start_x, self.drag_start_y, current_x, current_y)
        elif self.tool in ["line", "rectangle", "circle", "star", "arrow", "rounded_rectangle"]:
            # Show preview
            self._update_shape_preview(self.drag_start_x, self.drag_start_y, current_x, current_y)

        self.queue_draw()

    def _finish_shape(self, ctx):
        """Apply stroke or fill based on shape_fill_mode"""
        if self.shape_fill_mode == "filled":
            ctx.fill()
        else:
            ctx.stroke()

    def _update_shape_preview(self, x1, y1, x2, y2):
        """Draw shape preview on temporary surface"""
        self.preview_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(self.preview_surface)
        self._apply_antialiasing(ctx)
        r, g, b, a = self.fg_color
        ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        ctx.set_line_width(self.stroke_width)

        if self.tool == "line":
            ctx.move_to(x1, y1)
            ctx.line_to(x2, y2)
            ctx.stroke()
        elif self.tool == "rectangle":
            ctx.rectangle(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            self._finish_shape(ctx)
        elif self.tool == "circle":
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2
            ctx.arc(cx, cy, radius, 0, 2 * math.pi)
            self._finish_shape(ctx)
        elif self.tool == "star":
            self._draw_star_path(ctx, x1, y1, x2, y2)
            self._finish_shape(ctx)
        elif self.tool == "arrow":
            self._draw_arrow_path(ctx, x1, y1, x2, y2)
        elif self.tool == "rounded_rectangle":
            self._draw_rounded_rect_path(ctx, x1, y1, x2, y2)
            self._finish_shape(ctx)

    def _update_gradient_preview(self, x1, y1, x2, y2):
        """Draw gradient preview on temporary surface"""
        self.preview_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(self.preview_surface)
        r1, g1, b1, a1 = self.fg_color
        r2, g2, b2, a2 = self.bg_color
        if self.gradient_mode == "linear":
            pat = cairo.LinearGradient(x1, y1, x2, y2)
        else:
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2
            pat = cairo.RadialGradient(cx, cy, 0, cx, cy, max(1, radius))
        pat.add_color_stop_rgba(0, r1, g1, b1, a1 * self.brush_opacity * 0.6)
        pat.add_color_stop_rgba(1, r2, g2, b2, a2 * self.brush_opacity * 0.6)
        ctx.set_source(pat)
        ctx.paint()

    # ─── Drawing primitives ───

    def draw_star(self, x1, y1, x2, y2):
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self._draw_star_path(self.ctx, x1, y1, x2, y2)
        self._finish_shape(self.ctx)

    def _draw_star_path(self, ctx, x1, y1, x2, y2):
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2
        points = 10
        angle_step = 2 * math.pi / points
        for i in range(points):
            angle = i * angle_step - math.pi / 2
            r = radius if i % 2 == 0 else radius * 0.4
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            if i == 0:
                ctx.move_to(x, y)
            else:
                ctx.line_to(x, y)
        ctx.close_path()

    def draw_polygon(self):
        if len(self.polygon_points) < 3:
            return
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self.ctx.move_to(*self.polygon_points[0])
        for point in self.polygon_points[1:]:
            self.ctx.line_to(*point)
        self.ctx.close_path()
        self._finish_shape(self.ctx)

    def draw_arrow(self, x1, y1, x2, y2):
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self._draw_arrow_path(self.ctx, x1, y1, x2, y2)

    def _draw_arrow_path(self, ctx, x1, y1, x2, y2):
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()
        # Arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = max(10, self.line_width * 5)
        arrow_angle = math.pi / 6
        ax1 = x2 - arrow_len * math.cos(angle - arrow_angle)
        ay1 = y2 - arrow_len * math.sin(angle - arrow_angle)
        ax2 = x2 - arrow_len * math.cos(angle + arrow_angle)
        ay2 = y2 - arrow_len * math.sin(angle + arrow_angle)
        ctx.move_to(x2, y2)
        ctx.line_to(ax1, ay1)
        ctx.move_to(x2, y2)
        ctx.line_to(ax2, ay2)
        ctx.stroke()

    def draw_rounded_rectangle(self, x1, y1, x2, y2):
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self._draw_rounded_rect_path(self.ctx, x1, y1, x2, y2)
        self._finish_shape(self.ctx)

    def _draw_rounded_rect_path(self, ctx, x1, y1, x2, y2):
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        radius = min(w, h) * 0.2
        ctx.new_sub_path()
        ctx.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
        ctx.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
        ctx.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
        ctx.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        ctx.close_path()

    def flood_fill(self, x, y):
        """Flood fill using pixel-based approach"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        self.surface.flush()
        buf = self.surface.get_data()
        stride = self.surface.get_stride()

        # Get target color at click point
        offset = y * stride + x * 4
        target_b = buf[offset]
        target_g = buf[offset + 1]
        target_r = buf[offset + 2]
        target_a = buf[offset + 3]

        # Fill color
        r, g, b, a = self.fg_color
        fill_r = int(r * 255)
        fill_g = int(g * 255)
        fill_b = int(b * 255)
        fill_a = int(a * self.brush_opacity * 255)

        # Pre-multiply
        pm_r = fill_r * fill_a // 255
        pm_g = fill_g * fill_a // 255
        pm_b = fill_b * fill_a // 255

        if (target_r == pm_r and target_g == pm_g and
                target_b == pm_b and target_a == fill_a):
            return

        tolerance = self.fill_tolerance
        visited = set()
        stack = [(x, y)]

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if cx < 0 or cx >= self.width or cy < 0 or cy >= self.height:
                continue

            off = cy * stride + cx * 4
            cb = buf[off]
            cg = buf[off + 1]
            cr = buf[off + 2]
            ca = buf[off + 3]

            if (abs(cr - target_r) <= tolerance and
                    abs(cg - target_g) <= tolerance and
                    abs(cb - target_b) <= tolerance and
                    abs(ca - target_a) <= tolerance):
                buf[off] = pm_b
                buf[off + 1] = pm_g
                buf[off + 2] = pm_r
                buf[off + 3] = fill_a
                visited.add((cx, cy))
                stack.extend([(cx + 1, cy), (cx - 1, cy),
                              (cx, cy + 1), (cx, cy - 1)])

        self.surface.mark_dirty()
        self.queue_draw()

    def spray_paint(self, x, y):
        """Spray/airbrush tool — scattered dots"""
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity * 0.3)
        radius = self.brush_size * 2
        for _ in range(20):
            dx = random.gauss(0, radius / 2)
            dy = random.gauss(0, radius / 2)
            if dx * dx + dy * dy <= radius * radius:
                self.ctx.arc(x + dx, y + dy, 1, 0, 2 * math.pi)
                self.ctx.fill()
        self.queue_draw()

    def pick_color(self, x, y):
        """Pick color from canvas at position"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        self.surface.flush()
        buf = self.surface.get_data()
        stride = self.surface.get_stride()
        offset = y * stride + x * 4
        b_val = buf[offset]
        g_val = buf[offset + 1]
        r_val = buf[offset + 2]
        a_val = buf[offset + 3]
        # Un-premultiply
        if a_val > 0:
            r_f = min(1.0, r_val / a_val)
            g_f = min(1.0, g_val / a_val)
            b_f = min(1.0, b_val / a_val)
        else:
            r_f = g_f = b_f = 0.0
        a_f = a_val / 255.0
        self.fg_color = (r_f, g_f, b_f, a_f)
        if self.on_status_update:
            self.on_status_update()

    def draw_text(self, x, y):
        if not self.text_content:
            self.text_content = _("Text")
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.ctx.set_font_size(self.font_size)
        self.ctx.move_to(x, y)
        self.ctx.show_text(self.text_content)

    def draw_dot(self, x, y):
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        half = self.brush_size / 2
        if self.brush_shape == "square":
            self.ctx.rectangle(x - half, y - half, self.brush_size, self.brush_size)
        elif self.brush_shape == "calligraphy":
            # Angled ellipse for calligraphy effect
            self.ctx.save()
            self.ctx.translate(x, y)
            self.ctx.rotate(-math.pi / 4)
            self.ctx.scale(1, 3)
            self.ctx.arc(0, 0, half, 0, 2 * math.pi)
            self.ctx.restore()
        else:
            self.ctx.arc(x, y, half, 0, 2 * math.pi)
        self.ctx.fill()
        self.queue_draw()

    def erase_dot(self, x, y):
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.arc(x, y, self.brush_size, 0, 2 * math.pi)
        self.ctx.fill()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
        self.queue_draw()

    def draw_line_segment(self, x1, y1, x2, y2):
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        if self.brush_shape == "square":
            self.ctx.set_line_width(self.brush_size)
            self.ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
            self.ctx.move_to(x1, y1)
            self.ctx.line_to(x2, y2)
            self.ctx.stroke()
        elif self.brush_shape == "calligraphy":
            # Draw calligraphy stroke using stamped ellipses
            dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            steps = max(1, int(dist))
            half = self.brush_size / 2
            for i in range(steps + 1):
                t = i / max(1, steps)
                px = x1 + (x2 - x1) * t
                py = y1 + (y2 - y1) * t
                self.ctx.save()
                self.ctx.translate(px, py)
                self.ctx.rotate(-math.pi / 4)
                self.ctx.scale(1, 3)
                self.ctx.arc(0, 0, half, 0, 2 * math.pi)
                self.ctx.restore()
                self.ctx.fill()
        else:
            self.ctx.set_line_width(self.brush_size)
            self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            self.ctx.move_to(x1, y1)
            self.ctx.line_to(x2, y2)
            self.ctx.stroke()

    def erase_line_segment(self, x1, y1, x2, y2):
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.set_line_width(self.brush_size * 2)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.stroke()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def draw_line(self, x1, y1, x2, y2):
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.stroke()

    def draw_rectangle(self, x1, y1, x2, y2):
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self.ctx.rectangle(x, y, w, h)
        self._finish_shape(self.ctx)

    def draw_circle(self, x1, y1, x2, y2):
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self.ctx.arc(center_x, center_y, radius, 0, 2 * math.pi)
        self._finish_shape(self.ctx)

    def clear_canvas(self):
        self.save_state_for_undo()
        bg = self.settings.get("background_color", "white")
        if bg == "transparent":
            self.ctx.set_operator(cairo.OPERATOR_SOURCE)
            self.ctx.set_source_rgba(0, 0, 0, 0)
            self.ctx.paint()
            self.ctx.set_operator(cairo.OPERATOR_OVER)
        else:
            self.ctx.set_source_rgb(1, 1, 1)
            self.ctx.paint()
        self.selection = None
        self.selection_surface = None
        self.queue_draw()

    # ─── Selection operations ───

    def select_all(self):
        self.selection = (0, 0, self.width, self.height)
        self.queue_draw()

    def copy_selection(self):
        """Copy selected region to selection_surface"""
        if not self.selection:
            return
        sx, sy, sw, sh = [int(v) for v in self.selection]
        if sw <= 0 or sh <= 0:
            return
        self.selection_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        ctx = cairo.Context(self.selection_surface)
        ctx.set_source_surface(self.surface, -sx, -sy)
        ctx.paint()

    def cut_selection(self):
        """Cut selected region"""
        self.copy_selection()
        if not self.selection:
            return
        self.save_state_for_undo()
        sx, sy, sw, sh = self.selection
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        bg = self.settings.get("background_color", "white")
        if bg == "transparent":
            self.ctx.set_source_rgba(0, 0, 0, 0)
        else:
            self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.rectangle(sx, sy, sw, sh)
        self.ctx.fill()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
        self.queue_draw()

    def paste_selection(self):
        """Paste selection_surface onto canvas"""
        if not self.selection_surface:
            return
        self.save_state_for_undo()
        sx, sy = 0, 0
        if self.selection:
            sx, sy = self.selection[0], self.selection[1]
        self.ctx.set_source_surface(self.selection_surface, sx, sy)
        self.ctx.paint()
        self.selection = None
        self.selection_surface = None
        self.queue_draw()

    def delete_selection(self):
        """Delete selected region"""
        if not self.selection:
            return
        self.save_state_for_undo()
        sx, sy, sw, sh = self.selection
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        bg = self.settings.get("background_color", "white")
        if bg == "transparent":
            self.ctx.set_source_rgba(0, 0, 0, 0)
        else:
            self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.rectangle(sx, sy, sw, sh)
        self.ctx.fill()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
        self.selection = None
        self.queue_draw()

    def crop_to_selection(self):
        """Crop canvas to selection bounds"""
        if not self.selection:
            return
        sx, sy, sw, sh = [int(v) for v in self.selection]
        if sw <= 0 or sh <= 0:
            return
        self.save_state_for_undo()
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        ctx = cairo.Context(new_surface)
        ctx.set_source_surface(self.surface, -sx, -sy)
        ctx.paint()
        self.width = sw
        self.height = sh
        self.surface = new_surface
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)
        self.set_size_request(self.width, self.height)
        self.selection = None
        self.selection_surface = None
        self.undo_manager.save_state(self.surface)
        self.queue_draw()

    # ─── Canvas transforms ───

    def resize_canvas(self, new_width, new_height):
        """Resize canvas preserving content"""
        self.save_state_for_undo()
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, new_width, new_height)
        ctx = cairo.Context(new_surface)
        self._apply_antialiasing(ctx)
        bg = self.settings.get("background_color", "white")
        if bg == "transparent":
            ctx.set_source_rgba(0, 0, 0, 0)
        else:
            ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()
        self.width = new_width
        self.height = new_height
        self.surface = new_surface
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)
        self.set_size_request(self.width, self.height)
        self.queue_draw()

    def rotate_canvas(self, degrees):
        """Rotate canvas by 90, 180, or 270 degrees"""
        self.save_state_for_undo()
        if degrees in (90, 270):
            nw, nh = self.height, self.width
        else:
            nw, nh = self.width, self.height

        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, nw, nh)
        ctx = cairo.Context(new_surface)
        self._apply_antialiasing(ctx)

        if degrees == 90:
            ctx.translate(nw, 0)
            ctx.rotate(math.pi / 2)
        elif degrees == 180:
            ctx.translate(nw, nh)
            ctx.rotate(math.pi)
        elif degrees == 270:
            ctx.translate(0, nh)
            ctx.rotate(-math.pi / 2)

        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()

        self.width = nw
        self.height = nh
        self.surface = new_surface
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)
        self.set_size_request(self.width, self.height)
        self.queue_draw()

    def flip_canvas(self, horizontal=True):
        """Flip canvas horizontally or vertically"""
        self.save_state_for_undo()
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(new_surface)
        self._apply_antialiasing(ctx)

        if horizontal:
            ctx.translate(self.width, 0)
            ctx.scale(-1, 1)
        else:
            ctx.translate(0, self.height)
            ctx.scale(1, -1)

        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()

        self.surface = new_surface
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)
        self.queue_draw()

    # ─── Layer management ───

    def _get_active_surface(self):
        """Return the active layer's surface"""
        if self.layers and 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]["surface"]
        return self.surface

    def _sync_active_layer(self):
        """Keep self.surface/ctx pointing to the active layer"""
        self.surface = self._get_active_surface()
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)

    def add_layer(self, name=None):
        """Add a new transparent layer above the active one"""
        if name is None:
            name = _("Layer {}").format(len(self.layers) + 1)
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        # Transparent by default
        ctx = cairo.Context(new_surface)
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint()
        insert_idx = self.active_layer_index + 1
        self.layers.insert(insert_idx, {"name": name, "surface": new_surface, "visible": True})
        self.active_layer_index = insert_idx
        self._sync_active_layer()

    def delete_layer(self, index=None):
        """Delete a layer (cannot delete the last layer)"""
        if len(self.layers) <= 1:
            return
        if index is None:
            index = self.active_layer_index
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
            self._sync_active_layer()

    def set_active_layer(self, index):
        """Set the active layer by index"""
        if 0 <= index < len(self.layers):
            self.active_layer_index = index
            self._sync_active_layer()

    def flatten_layers(self):
        """Flatten all layers into a single surface"""
        flat = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(flat)
        self._apply_antialiasing(ctx)
        # Fill background
        bg = self.settings.get("background_color", "white")
        if bg == "transparent":
            ctx.set_source_rgba(0, 0, 0, 0)
        else:
            ctx.set_source_rgb(1, 1, 1)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)
        for layer in self.layers:
            if layer["visible"]:
                ctx.set_source_surface(layer["surface"], 0, 0)
                ctx.paint()
        return flat

    # ─── Crop tool ───

    def start_crop(self, x1, y1, x2, y2):
        """Set the pending crop rectangle"""
        sx = min(x1, x2)
        sy = min(y1, y2)
        sw = abs(x2 - x1)
        sh = abs(y2 - y1)
        if sw > 2 and sh > 2:
            self.crop_rect = (sx, sy, sw, sh)
            self.queue_draw()

    def confirm_crop(self):
        """Confirm the pending crop"""
        if not self.crop_rect:
            return
        sx, sy, sw, sh = [int(v) for v in self.crop_rect]
        if sw <= 0 or sh <= 0:
            return
        self.save_state_for_undo()
        # Crop all layers
        new_layers = []
        for layer in self.layers:
            new_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
            ctx = cairo.Context(new_surf)
            ctx.set_source_surface(layer["surface"], -sx, -sy)
            ctx.paint()
            new_layers.append({"name": layer["name"], "surface": new_surf, "visible": layer["visible"]})
        self.layers = new_layers
        self.width = sw
        self.height = sh
        self._sync_active_layer()
        self.set_size_request(self.width, self.height)
        self.crop_rect = None
        self.undo_manager.save_state(self.surface)
        self.queue_draw()

    def cancel_crop(self):
        """Cancel the pending crop"""
        self.crop_rect = None
        self.queue_draw()

    # ─── Gradient tool ───

    def draw_gradient(self, x1, y1, x2, y2):
        """Draw a gradient from fg_color to bg_color"""
        self.save_state_for_undo()
        r1, g1, b1, a1 = self.fg_color
        r2, g2, b2, a2 = self.bg_color

        if self.gradient_mode == "linear":
            pat = cairo.LinearGradient(x1, y1, x2, y2)
        else:
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2
            pat = cairo.RadialGradient(cx, cy, 0, cx, cy, radius)

        pat.add_color_stop_rgba(0, r1, g1, b1, a1 * self.brush_opacity)
        pat.add_color_stop_rgba(1, r2, g2, b2, a2 * self.brush_opacity)

        self.ctx.set_source(pat)
        self.ctx.paint()
        self.queue_draw()

    # ─── File I/O ───

    def save_image(self, filename):
        """Save canvas to file in the appropriate format (flattens layers)"""
        flat_surface = self.flatten_layers()
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.png':
            flat_surface.write_to_png(filename)
        else:
            # Use GdkPixbuf for non-PNG formats
            flat_surface.flush()
            w, h = self.width, self.height
            data = bytes(flat_surface.get_data())
            # Convert BGRA premultiplied to RGBA
            rgba_data = bytearray(w * h * 4)
            stride = flat_surface.get_stride()
            for y in range(h):
                for x in range(w):
                    src_off = y * stride + x * 4
                    dst_off = (y * w + x) * 4
                    b_val = data[src_off]
                    g_val = data[src_off + 1]
                    r_val = data[src_off + 2]
                    a_val = data[src_off + 3]
                    # Un-premultiply
                    if a_val > 0:
                        r_val = min(255, r_val * 255 // a_val)
                        g_val = min(255, g_val * 255 // a_val)
                        b_val = min(255, b_val * 255 // a_val)
                    rgba_data[dst_off] = r_val
                    rgba_data[dst_off + 1] = g_val
                    rgba_data[dst_off + 2] = b_val
                    rgba_data[dst_off + 3] = a_val

            pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                bytes(rgba_data), GdkPixbuf.Colorspace.RGB, True, 8,
                w, h, w * 4)

            if ext in ('.jpg', '.jpeg'):
                quality = str(self.settings.get("jpeg_quality", 90))
                pixbuf.savev(filename, "jpeg", ["quality"], [quality])
            elif ext == '.bmp':
                pixbuf.savev(filename, "bmp", [], [])
            elif ext in ('.tif', '.tiff'):
                pixbuf.savev(filename, "tiff", [], [])
            elif ext == '.ico':
                pixbuf.savev(filename, "ico", [], [])
            elif ext == '.webp':
                pixbuf.savev(filename, "webp", [], [])
            else:
                self.surface.write_to_png(filename)

    def save_image_with_dimensions(self, filename, export_width, export_height):
        """Save with specific dimensions (resize on export)"""
        self.surface.flush()
        w, h = self.width, self.height
        data = bytes(self.surface.get_data())
        stride = self.surface.get_stride()
        rgba_data = bytearray(w * h * 4)
        for y in range(h):
            for x in range(w):
                src_off = y * stride + x * 4
                dst_off = (y * w + x) * 4
                b_val = data[src_off]
                g_val = data[src_off + 1]
                r_val = data[src_off + 2]
                a_val = data[src_off + 3]
                if a_val > 0:
                    r_val = min(255, r_val * 255 // a_val)
                    g_val = min(255, g_val * 255 // a_val)
                    b_val = min(255, b_val * 255 // a_val)
                rgba_data[dst_off] = r_val
                rgba_data[dst_off + 1] = g_val
                rgba_data[dst_off + 2] = b_val
                rgba_data[dst_off + 3] = a_val

        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            bytes(rgba_data), GdkPixbuf.Colorspace.RGB, True, 8,
            w, h, w * 4)
        scaled = pixbuf.scale_simple(export_width, export_height,
                                     GdkPixbuf.InterpType.BILINEAR)
        ext = os.path.splitext(filename)[1].lower()
        fmt = "png"
        if ext in ('.jpg', '.jpeg'):
            fmt = "jpeg"
        elif ext == '.bmp':
            fmt = "bmp"
        elif ext in ('.tif', '.tiff'):
            fmt = "tiff"
        elif ext == '.ico':
            fmt = "ico"
        elif ext == '.webp':
            fmt = "webp"
        scaled.savev(filename, fmt, [], [])

    def load_image(self, filename):
        """Load image into canvas using GdkPixbuf"""
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            self.save_state_for_undo()

            pw = pixbuf.get_width()
            ph = pixbuf.get_height()
            has_alpha = pixbuf.get_has_alpha()
            n_channels = pixbuf.get_n_channels()
            rowstride = pixbuf.get_rowstride()

            # Resize canvas if image is larger
            if pw != self.width or ph != self.height:
                self.width = pw
                self.height = ph
                self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw, ph)
                self.ctx = cairo.Context(self.surface)
                self._apply_antialiasing(self.ctx)
                self.set_size_request(pw, ph)

            img_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw, ph)
            pixels = pixbuf.get_pixels()
            buf = img_surface.get_data()

            for y in range(ph):
                for x in range(pw):
                    src_offset = y * rowstride + x * n_channels
                    r = pixels[src_offset]
                    g = pixels[src_offset + 1]
                    b = pixels[src_offset + 2]
                    a = pixels[src_offset + 3] if has_alpha else 255

                    dst_offset = y * img_surface.get_stride() + x * 4
                    buf[dst_offset] = b * a // 255
                    buf[dst_offset + 1] = g * a // 255
                    buf[dst_offset + 2] = r * a // 255
                    buf[dst_offset + 3] = a

            img_surface.mark_dirty()
            self.ctx.set_operator(cairo.OPERATOR_SOURCE)
            self.ctx.set_source_surface(img_surface, 0, 0)
            self.ctx.paint()
            self.ctx.set_operator(cairo.OPERATOR_OVER)
            self.queue_draw()
        except Exception as e:
            print(f"Error loading image: {e}")


class ColorSwatchButton(Gtk.Button):
    """Color swatch button for palette"""

    def __init__(self, color_rgba, callback):
        super().__init__()
        self.color_rgba = color_rgba
        self.callback = callback

        swatch = Gtk.DrawingArea()
        swatch.set_size_request(20, 20)
        swatch.set_draw_func(self._draw)
        self.set_child(swatch)
        self.connect("clicked", self._on_click)

    def _draw(self, area, ctx, w, h, data=None):
        # Checkerboard for transparency
        if len(self.color_rgba) == 4 and self.color_rgba[3] < 1.0:
            ctx.set_source_rgb(0.8, 0.8, 0.8)
            ctx.paint()
            ctx.set_source_rgb(0.6, 0.6, 0.6)
            for cy in range(0, h, 4):
                for cx in range(0, w, 4):
                    if (cx // 4 + cy // 4) % 2 == 0:
                        ctx.rectangle(cx, cy, 4, 4)
            ctx.fill()
        r, g, b = self.color_rgba[0], self.color_rgba[1], self.color_rgba[2]
        a = self.color_rgba[3] if len(self.color_rgba) == 4 else 1.0
        ctx.set_source_rgba(r, g, b, a)
        ctx.paint()

    def _on_click(self, btn):
        self.callback(self.color_rgba)

    def set_color(self, color_rgba):
        self.color_rgba = color_rgba
        child = self.get_child()
        if child:
            child.queue_draw()


class FgBgColorWidget(Gtk.DrawingArea):
    """Foreground/background color indicator with swap"""

    def __init__(self, drawing_area):
        super().__init__()
        self.da = drawing_area
        self.set_size_request(48, 48)
        self.set_draw_func(self._draw)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_click)
        self.add_controller(click)

    def _draw(self, area, ctx, w, h, data=None):
        # Background color (bottom-right)
        r, g, b, a = self.da.bg_color
        ctx.set_source_rgba(r, g, b, a)
        ctx.rectangle(w * 0.3, h * 0.3, w * 0.65, h * 0.65)
        ctx.fill_preserve()
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1)
        ctx.stroke()

        # Foreground color (top-left)
        r, g, b, a = self.da.fg_color
        ctx.set_source_rgba(r, g, b, a)
        ctx.rectangle(w * 0.05, h * 0.05, w * 0.6, h * 0.6)
        ctx.fill_preserve()
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1)
        ctx.stroke()

    def _on_click(self, gesture, n_press, x, y):
        # Click on top-right corner area to swap
        w = self.get_width()
        if x > w * 0.6:
            self.da.fg_color, self.da.bg_color = self.da.bg_color, self.da.fg_color
            self.queue_draw()


class TextInputDialog(Adw.MessageDialog):
    """Dialog for text input"""

    def __init__(self, parent, current_text=""):
        super().__init__(transient_for=parent)
        self.set_heading(_("Enter Text"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("OK"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        self.text_entry = Gtk.Entry()
        self.text_entry.set_text(current_text)
        self.text_entry.set_placeholder_text(_("Enter text to draw"))

        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        font_label = Gtk.Label(label=_("Font Size:"))
        self.font_entry = Gtk.SpinButton.new_with_range(8, 200, 1)
        self.font_entry.set_value(16)
        font_box.append(font_label)
        font_box.append(self.font_entry)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.append(self.text_entry)
        content_box.append(font_box)
        self.set_extra_child(content_box)

    def get_text(self):
        return self.text_entry.get_text()

    def get_font_size(self):
        return int(self.font_entry.get_value())


class CanvasResizeDialog(Adw.MessageDialog):
    """Dialog for canvas resize with aspect ratio lock"""

    def __init__(self, parent, current_width, current_height):
        super().__init__(transient_for=parent)
        self.set_heading(_("Resize Canvas"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("OK"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        self._aspect_ratio = current_width / max(1, current_height)
        self._updating = False

        grid = Gtk.Grid(row_spacing=8, column_spacing=12)

        grid.attach(Gtk.Label(label=_("Width:")), 0, 0, 1, 1)
        self.width_spin = Gtk.SpinButton.new_with_range(1, 10000, 1)
        self.width_spin.set_value(current_width)
        grid.attach(self.width_spin, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label=_("Height:")), 0, 1, 1, 1)
        self.height_spin = Gtk.SpinButton.new_with_range(1, 10000, 1)
        self.height_spin.set_value(current_height)
        grid.attach(self.height_spin, 1, 1, 1, 1)

        # Aspect ratio lock
        self.lock_check = Gtk.CheckButton(label=_("Lock aspect ratio"))
        grid.attach(self.lock_check, 0, 2, 2, 1)

        self.width_spin.connect("value-changed", self._on_width_changed)
        self.height_spin.connect("value-changed", self._on_height_changed)

        self.set_extra_child(grid)

    def _on_width_changed(self, spin):
        if self._updating or not self.lock_check.get_active():
            return
        self._updating = True
        new_h = int(spin.get_value() / self._aspect_ratio)
        self.height_spin.set_value(max(1, new_h))
        self._updating = False

    def _on_height_changed(self, spin):
        if self._updating or not self.lock_check.get_active():
            return
        self._updating = True
        new_w = int(spin.get_value() * self._aspect_ratio)
        self.width_spin.set_value(max(1, new_w))
        self._updating = False

    def get_dimensions(self):
        return int(self.width_spin.get_value()), int(self.height_spin.get_value())


class ExportDialog(Adw.MessageDialog):
    """Dialog for export with custom dimensions"""

    def __init__(self, parent, current_width, current_height):
        super().__init__(transient_for=parent)
        self.set_heading(_("Export with Dimensions"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Export"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        grid = Gtk.Grid(row_spacing=8, column_spacing=12)

        grid.attach(Gtk.Label(label=_("Width:")), 0, 0, 1, 1)
        self.width_spin = Gtk.SpinButton.new_with_range(1, 10000, 1)
        self.width_spin.set_value(current_width)
        grid.attach(self.width_spin, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label=_("Height:")), 0, 1, 1, 1)
        self.height_spin = Gtk.SpinButton.new_with_range(1, 10000, 1)
        self.height_spin.set_value(current_height)
        grid.attach(self.height_spin, 1, 1, 1, 1)

        self.set_extra_child(grid)

    def get_dimensions(self):
        return int(self.width_spin.get_value()), int(self.height_spin.get_value())


class JpegQualityDialog(Adw.MessageDialog):
    """Dialog for JPEG quality setting"""

    def __init__(self, parent):
        super().__init__(transient_for=parent)
        self.set_heading(_("JPEG Quality"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Save"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.append(Gtk.Label(label=_("Quality:")))
        self.quality_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.quality_scale.set_value(90)
        self.quality_scale.set_size_request(200, -1)
        self.quality_scale.set_hexpand(True)
        box.append(self.quality_scale)
        self.set_extra_child(box)

    def get_quality(self):
        return int(self.quality_scale.get_value())


class PreferencesDialog(Adw.PreferencesWindow):
    """Application preferences dialog"""

    def __init__(self, parent, settings):
        super().__init__(transient_for=parent)
        self.settings = settings
        self.set_title(_("Preferences"))
        self.set_default_size(500, 600)

        # Canvas page
        canvas_page = Adw.PreferencesPage()
        canvas_page.set_title(_("Canvas"))
        canvas_page.set_icon_name("applications-graphics-symbolic")

        canvas_group = Adw.PreferencesGroup()
        canvas_group.set_title(_("Default Canvas"))

        # Canvas width
        self.width_row = Adw.SpinRow.new_with_range(100, 10000, 100)
        self.width_row.set_title(_("Width"))
        self.width_row.set_value(settings.get("canvas_width", 800))
        canvas_group.add(self.width_row)

        # Canvas height
        self.height_row = Adw.SpinRow.new_with_range(100, 10000, 100)
        self.height_row.set_title(_("Height"))
        self.height_row.set_value(settings.get("canvas_height", 600))
        canvas_group.add(self.height_row)

        # Background color
        self.bg_row = Adw.ComboRow()
        self.bg_row.set_title(_("Default Background"))
        bg_model = Gtk.StringList.new([_("White"), _("Transparent")])
        self.bg_row.set_model(bg_model)
        current_bg = settings.get("background_color", "white")
        self.bg_row.set_selected(1 if current_bg == "transparent" else 0)
        canvas_group.add(self.bg_row)

        # Grid size
        self.grid_row = Adw.SpinRow.new_with_range(5, 100, 5)
        self.grid_row.set_title(_("Grid Size"))
        self.grid_row.set_value(settings.get("grid_size", 20))
        canvas_group.add(self.grid_row)

        canvas_page.add(canvas_group)
        self.add(canvas_page)

        # General page
        general_page = Adw.PreferencesPage()
        general_page.set_title(_("General"))
        general_page.set_icon_name("preferences-system-symbolic")

        save_group = Adw.PreferencesGroup()
        save_group.set_title(_("Saving"))

        # Auto-save interval
        self.autosave_row = Adw.ComboRow()
        self.autosave_row.set_title(_("Auto-save Interval"))
        autosave_model = Gtk.StringList.new([
            _("Off"), _("1 minute"), _("5 minutes"), _("10 minutes")])
        self.autosave_row.set_model(autosave_model)
        interval = settings.get("auto_save_interval", 0)
        idx = {0: 0, 1: 1, 5: 2, 10: 3}.get(interval, 0)
        self.autosave_row.set_selected(idx)
        save_group.add(self.autosave_row)

        # Default save format
        self.format_row = Adw.ComboRow()
        self.format_row.set_title(_("Default Save Format"))
        format_model = Gtk.StringList.new(["PNG", "JPEG", "BMP", "TIFF", "ICO"])
        self.format_row.set_model(format_model)
        fmt = settings.get("default_save_format", "png")
        fmt_idx = {"png": 0, "jpeg": 1, "bmp": 2, "tiff": 3, "ico": 4}.get(fmt, 0)
        self.format_row.set_selected(fmt_idx)
        save_group.add(self.format_row)

        general_page.add(save_group)

        # Undo group
        undo_group = Adw.PreferencesGroup()
        undo_group.set_title(_("History"))

        self.undo_row = Adw.SpinRow.new_with_range(5, 200, 5)
        self.undo_row.set_title(_("Undo History Limit"))
        self.undo_row.set_value(settings.get("undo_history_limit", 50))
        undo_group.add(self.undo_row)

        general_page.add(undo_group)
        self.add(general_page)

        # Drawing page
        drawing_page = Adw.PreferencesPage()
        drawing_page.set_title(_("Drawing"))
        drawing_page.set_icon_name("edit-symbolic")

        drawing_group = Adw.PreferencesGroup()
        drawing_group.set_title(_("Quality"))

        # Antialiasing
        self.aa_row = Adw.SwitchRow()
        self.aa_row.set_title(_("Antialiasing"))
        self.aa_row.set_active(settings.get("antialiasing", True))
        drawing_group.add(self.aa_row)

        # Brush interpolation
        self.interp_row = Adw.ComboRow()
        self.interp_row.set_title(_("Brush Interpolation"))
        interp_model = Gtk.StringList.new([_("Fast"), _("Good"), _("Best")])
        self.interp_row.set_model(interp_model)
        interp = settings.get("brush_interpolation", "good")
        interp_idx = {"fast": 0, "good": 1, "best": 2}.get(interp, 1)
        self.interp_row.set_selected(interp_idx)
        drawing_group.add(self.interp_row)

        drawing_page.add(drawing_group)
        self.add(drawing_page)

        self.connect("close-request", self._on_close)

    def _on_close(self, *args):
        self.settings["canvas_width"] = int(self.width_row.get_value())
        self.settings["canvas_height"] = int(self.height_row.get_value())
        self.settings["background_color"] = "transparent" if self.bg_row.get_selected() == 1 else "white"
        self.settings["grid_size"] = int(self.grid_row.get_value())

        autosave_map = {0: 0, 1: 1, 2: 5, 3: 10}
        self.settings["auto_save_interval"] = autosave_map.get(
            self.autosave_row.get_selected(), 0)

        format_map = {0: "png", 1: "jpeg", 2: "bmp", 3: "tiff", 4: "ico"}
        self.settings["default_save_format"] = format_map.get(
            self.format_row.get_selected(), "png")

        self.settings["undo_history_limit"] = int(self.undo_row.get_value())
        self.settings["antialiasing"] = self.aa_row.get_active()

        interp_map = {0: "fast", 1: "good", 2: "best"}
        self.settings["brush_interpolation"] = interp_map.get(
            self.interp_row.get_selected(), "good")

        _save_settings(self.settings)
        return False


class PaintBrushWindow(Adw.ApplicationWindow):
    """Enhanced main window with advanced tools"""

    def __init__(self, app):
        super().__init__(application=app)

        self.settings = app.settings
        self.set_title(_("PaintBrush"))
        self.set_default_size(1100, 750)

        self.current_file = None
        self.auto_save_id = None

        # Create drawing area
        self.drawing_area = DrawingArea(self.settings)
        self.drawing_area.on_status_update = self.update_status_bar

        # Recent colors list
        self.recent_color_buttons = []

        # Setup UI
        self.setup_ui()
        self.setup_actions()
        self.setup_shortcuts()
        self.setup_auto_save()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Basic shortcuts (actions)
        action_defs = [
            ("undo", self.on_undo),
            ("redo", self.on_redo),
            ("zoom_in", self.on_zoom_in),
            ("zoom_out", self.on_zoom_out),
            ("zoom_reset", self.on_zoom_reset),
            ("show-shortcuts", self.on_show_shortcuts),
            ("toggle_grid", self.on_toggle_grid),
            ("select_all", self.on_select_all),
            ("delete_selection", self.on_delete_selection),
            ("copy", self.on_copy),
            ("paste", self.on_paste),
            ("cut", self.on_cut),
            ("brush_size_up", self.on_brush_size_up),
            ("brush_size_down", self.on_brush_size_down),
            ("reset_colors", self.on_reset_colors),
            ("swap_colors", self.on_swap_colors),
            ("confirm_crop", self.on_confirm_crop),
            ("cancel_crop", self.on_cancel_crop),
        ]
        for name, callback in action_defs:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        # Tool shortcuts
        tool_keys = {
            "tool_brush": "brush",
            "tool_eraser": "eraser",
            "tool_line": "line",
            "tool_rectangle": "rectangle",
            "tool_circle": "circle",
            "tool_text": "text",
            "tool_fill": "fill",
            "tool_star": "star",
            "tool_polygon": "polygon",
            "tool_select": "select",
            "tool_eyedropper": "eyedropper",
            "tool_spray": "spray",
            "tool_arrow": "arrow",
            "tool_rounded_rectangle": "rounded_rectangle",
            "tool_crop": "crop",
            "tool_gradient": "gradient",
        }
        for action_name, tool_id in tool_keys.items():
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", self._on_tool_shortcut, tool_id)
            self.add_action(action)

    def _on_tool_shortcut(self, action, param, tool_id):
        btn = self.tool_buttons.get(tool_id)
        if btn:
            btn.set_active(True)

    def on_show_shortcuts(self, action, param):
        """Show keyboard shortcuts window"""
        builder = Gtk.Builder.new_from_string('''
        <interface>
          <object class="GtkShortcutsWindow" id="shortcuts">
            <property name="modal">True</property>
            <child>
              <object class="GtkShortcutsSection">
                <property name="section-name">shortcuts</property>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">File</property>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">New</property>
                        <property name="accelerator">&lt;Primary&gt;n</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Open</property>
                        <property name="accelerator">&lt;Primary&gt;o</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Save</property>
                        <property name="accelerator">&lt;Primary&gt;s</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Save As</property>
                        <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;s</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Quit</property>
                        <property name="accelerator">&lt;Primary&gt;q</property>
                    </object></child>
                  </object>
                </child>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">Edit</property>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Undo</property>
                        <property name="accelerator">&lt;Primary&gt;z</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Redo</property>
                        <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;z</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Select All</property>
                        <property name="accelerator">&lt;Primary&gt;a</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Copy</property>
                        <property name="accelerator">&lt;Primary&gt;c</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Paste</property>
                        <property name="accelerator">&lt;Primary&gt;v</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Cut</property>
                        <property name="accelerator">&lt;Primary&gt;x</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Delete Selection</property>
                        <property name="accelerator">Delete</property>
                    </object></child>
                  </object>
                </child>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">View</property>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Zoom In</property>
                        <property name="accelerator">&lt;Primary&gt;plus</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Zoom Out</property>
                        <property name="accelerator">&lt;Primary&gt;minus</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Reset Zoom</property>
                        <property name="accelerator">&lt;Primary&gt;0</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Toggle Grid</property>
                        <property name="accelerator">&lt;Primary&gt;g</property>
                    </object></child>
                  </object>
                </child>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">Tools</property>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Brush</property>
                        <property name="accelerator">b</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Eraser</property>
                        <property name="accelerator">e</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Line</property>
                        <property name="accelerator">l</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Rectangle</property>
                        <property name="accelerator">r</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Circle</property>
                        <property name="accelerator">c</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Text</property>
                        <property name="accelerator">t</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Fill</property>
                        <property name="accelerator">f</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Star</property>
                        <property name="accelerator">s</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Polygon</property>
                        <property name="accelerator">p</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Eyedropper</property>
                        <property name="accelerator">i</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Selection</property>
                        <property name="accelerator">m</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Spray</property>
                        <property name="accelerator">a</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Arrow</property>
                        <property name="accelerator">w</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Crop</property>
                        <property name="accelerator">&lt;Shift&gt;c</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Gradient</property>
                        <property name="accelerator">g</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Confirm Crop</property>
                        <property name="accelerator">Return</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Rotate 90°</property>
                        <property name="accelerator">&lt;Primary&gt;r</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Decrease Brush Size</property>
                        <property name="accelerator">bracketleft</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Increase Brush Size</property>
                        <property name="accelerator">bracketright</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Reset Colors</property>
                        <property name="accelerator">d</property>
                    </object></child>
                    <child><object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Swap Colors</property>
                        <property name="accelerator">x</property>
                    </object></child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </interface>
        ''', -1)
        shortcuts = builder.get_object("shortcuts")
        shortcuts.set_transient_for(self)
        shortcuts.present()

    def setup_ui(self):
        """Create the user interface"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu = Gio.Menu()

        file_section = Gio.Menu()
        file_section.append(_("New"), "win.new")
        file_section.append(_("Open"), "win.open")
        file_section.append(_("Save"), "win.save")
        file_section.append(_("Save As"), "win.save_as")
        file_section.append(_("Export…"), "win.export")
        menu.append_section(None, file_section)

        # Recent files submenu
        self.recent_menu = Gio.Menu()
        recent_files = self.settings.get("recent_files", [])
        for i, fpath in enumerate(recent_files[:10]):
            self.recent_menu.append(os.path.basename(fpath), f"win.open_recent_{i}")
        if recent_files:
            menu.append_submenu(_("Recent Files"), self.recent_menu)

        edit_section = Gio.Menu()
        edit_section.append(_("Undo"), "win.undo")
        edit_section.append(_("Redo"), "win.redo")
        edit_section.append(_("Select All"), "win.select_all")
        edit_section.append(_("Copy"), "win.copy")
        edit_section.append(_("Paste"), "win.paste")
        edit_section.append(_("Cut"), "win.cut")
        menu.append_section(None, edit_section)

        zoom_section = Gio.Menu()
        zoom_section.append(_("Zoom In"), "win.zoom_in")
        zoom_section.append(_("Zoom Out"), "win.zoom_out")
        zoom_section.append(_("Zoom Reset"), "win.zoom_reset")
        zoom_section.append(_("Toggle Grid"), "win.toggle_grid")
        menu.append_section(None, zoom_section)

        canvas_section = Gio.Menu()
        canvas_section.append(_("Clear Canvas"), "win.clear")
        canvas_section.append(_("Resize Canvas…"), "win.resize_canvas")
        canvas_section.append(_("Crop to Selection"), "win.crop_to_selection")
        menu.append_section(None, canvas_section)

        transform_section = Gio.Menu()
        transform_section.append(_("Rotate 90°"), "win.rotate_90")
        transform_section.append(_("Rotate 180°"), "win.rotate_180")
        transform_section.append(_("Rotate 270°"), "win.rotate_270")
        transform_section.append(_("Flip Horizontal"), "win.flip_h")
        transform_section.append(_("Flip Vertical"), "win.flip_v")
        menu.append_section(None, transform_section)

        app_section = Gio.Menu()
        app_section.append(_("Preferences"), "win.preferences")
        app_section.append(_("Keyboard Shortcuts"), "win.show-shortcuts")
        app_section.append(_("About PaintBrush"), "app.about")
        app_section.append(_("Quit"), "app.quit")
        menu.append_section(None, app_section)

        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Content with sidebar
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.append(content_box)

        # Left sidebar — tools and colors
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_margin_start(6)
        sidebar.set_margin_top(6)
        sidebar.set_margin_bottom(6)
        sidebar.set_size_request(200, -1)

        # Scrolled sidebar content
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_vexpand(True)

        sidebar_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar_scroll.set_child(sidebar_inner)
        sidebar.append(sidebar_scroll)
        content_box.append(sidebar)

        # Tools section
        tools_label = Gtk.Label(label=_("Tools:"))
        tools_label.add_css_class("heading")
        tools_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(tools_label)

        self.tool_buttons = {}
        tools = [
            ("brush", _("Brush"), "edit-symbolic"),
            ("eraser", _("Eraser"), "edit-clear-symbolic"),
            ("line", _("Line"), "line-symbolic"),
            ("rectangle", _("Rectangle"), "view-grid-symbolic"),
            ("rounded_rectangle", _("Rounded Rectangle"), "view-grid-symbolic"),
            ("circle", _("Circle"), "media-record-symbolic"),
            ("polygon", _("Polygon"), "path-symbolic"),
            ("star", _("Star"), "starred-symbolic"),
            ("arrow", _("Arrow"), "go-next-symbolic"),
            ("fill", _("Fill"), "paint-bucket-symbolic"),
            ("text", _("Text"), "text-symbolic"),
            ("select", _("Selection"), "selection-mode-symbolic"),
            ("eyedropper", _("Eyedropper"), "color-select-symbolic"),
            ("spray", _("Spray"), "weather-fog-symbolic"),
            ("crop", _("Crop"), "edit-cut-symbolic"),
            ("gradient", _("Gradient"), "color-profile-symbolic"),
        ]

        tool_flow = Gtk.FlowBox()
        tool_flow.set_max_children_per_line(4)
        tool_flow.set_selection_mode(Gtk.SelectionMode.NONE)

        for tool_id, label, icon in tools:
            btn = Gtk.ToggleButton()
            btn.set_icon_name(icon)
            btn.set_tooltip_text(label)
            btn.connect("toggled", self.on_tool_changed, tool_id)
            tool_flow.insert(btn, -1)
            self.tool_buttons[tool_id] = btn

        sidebar_inner.append(tool_flow)
        self.tool_buttons["brush"].set_active(True)

        sidebar_inner.append(Gtk.Separator())

        # Brush size
        size_label = Gtk.Label(label=_("Size:"))
        size_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(size_label)

        self.size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 50, 1)
        self.size_scale.set_value(5)
        self.size_scale.connect("value-changed", self.on_size_changed)
        sidebar_inner.append(self.size_scale)

        # Opacity slider
        opacity_label = Gtk.Label(label=_("Opacity:"))
        opacity_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(opacity_label)

        self.opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.opacity_scale.set_value(100)
        self.opacity_scale.connect("value-changed", self.on_opacity_changed)
        sidebar_inner.append(self.opacity_scale)

        # Stroke width for shape tools
        stroke_label = Gtk.Label(label=_("Stroke Width:"))
        stroke_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(stroke_label)

        self.stroke_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 30, 1)
        self.stroke_scale.set_value(2)
        self.stroke_scale.connect("value-changed", self.on_stroke_width_changed)
        sidebar_inner.append(self.stroke_scale)

        # Fill vs outline toggle
        fill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fill_label = Gtk.Label(label=_("Shape:"))
        fill_box.append(fill_label)

        self.outline_btn = Gtk.ToggleButton(label=_("Outline"))
        self.outline_btn.set_active(True)
        self.outline_btn.connect("toggled", self.on_fill_mode_changed, "outline")
        fill_box.append(self.outline_btn)

        self.filled_btn = Gtk.ToggleButton(label=_("Filled"))
        self.filled_btn.connect("toggled", self.on_fill_mode_changed, "filled")
        fill_box.append(self.filled_btn)
        sidebar_inner.append(fill_box)

        # Brush shape selector
        brush_shape_label = Gtk.Label(label=_("Brush Shape:"))
        brush_shape_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(brush_shape_label)

        brush_shape_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.brush_shape_buttons = {}
        for shape_id, shape_name in [("round", _("Round")), ("square", _("Square")), ("calligraphy", _("Calligraphy"))]:
            btn = Gtk.ToggleButton(label=shape_name)
            btn.connect("toggled", self.on_brush_shape_changed, shape_id)
            brush_shape_box.append(btn)
            self.brush_shape_buttons[shape_id] = btn
        self.brush_shape_buttons["round"].set_active(True)
        sidebar_inner.append(brush_shape_box)

        # Gradient mode selector
        gradient_label = Gtk.Label(label=_("Gradient:"))
        gradient_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(gradient_label)

        gradient_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.gradient_buttons = {}
        for gid, gname in [("linear", _("Linear")), ("radial", _("Radial"))]:
            btn = Gtk.ToggleButton(label=gname)
            btn.connect("toggled", self.on_gradient_mode_changed, gid)
            gradient_box.append(btn)
            self.gradient_buttons[gid] = btn
        self.gradient_buttons["linear"].set_active(True)
        sidebar_inner.append(gradient_box)

        sidebar_inner.append(Gtk.Separator())

        # Layers section
        layers_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        layers_label = Gtk.Label(label=_("Layers:"))
        layers_label.set_halign(Gtk.Align.START)
        layers_label.set_hexpand(True)
        layers_header.append(layers_label)

        add_layer_btn = Gtk.Button()
        add_layer_btn.set_icon_name("list-add-symbolic")
        add_layer_btn.set_tooltip_text(_("Add Layer"))
        add_layer_btn.connect("clicked", self.on_add_layer)
        layers_header.append(add_layer_btn)

        del_layer_btn = Gtk.Button()
        del_layer_btn.set_icon_name("list-remove-symbolic")
        del_layer_btn.set_tooltip_text(_("Delete Layer"))
        del_layer_btn.connect("clicked", self.on_delete_layer)
        layers_header.append(del_layer_btn)

        sidebar_inner.append(layers_header)

        self.layer_list_box = Gtk.ListBox()
        self.layer_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.layer_list_box.connect("row-selected", self.on_layer_selected)
        sidebar_inner.append(self.layer_list_box)
        self._rebuild_layer_list()

        sidebar_inner.append(Gtk.Separator())

        # Foreground/Background color indicator
        color_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        colors_label = Gtk.Label(label=_("Colors:"))
        colors_label.set_halign(Gtk.Align.START)
        color_header.append(colors_label)

        # Swap button
        swap_btn = Gtk.Button()
        swap_btn.set_icon_name("object-flip-horizontal-symbolic")
        swap_btn.set_tooltip_text(_("Swap Colors"))
        swap_btn.connect("clicked", lambda b: self._swap_colors())
        color_header.append(swap_btn)

        # Custom color button (opens color dialog)
        custom_color_btn = Gtk.Button()
        custom_color_btn.set_icon_name("color-select-symbolic")
        custom_color_btn.set_tooltip_text(_("Custom Color…"))
        custom_color_btn.connect("clicked", self.on_custom_color)
        color_header.append(custom_color_btn)

        sidebar_inner.append(color_header)

        # FG/BG indicator
        self.fg_bg_widget = FgBgColorWidget(self.drawing_area)
        sidebar_inner.append(self.fg_bg_widget)

        # Color palette (48 colors, 8 per row)
        palette_grid = Gtk.FlowBox()
        palette_grid.set_max_children_per_line(8)
        palette_grid.set_min_children_per_line(8)
        palette_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        palette_grid.set_homogeneous(True)

        for color in DEFAULT_PALETTE:
            rgba = (color[0], color[1], color[2], 1.0)
            btn = ColorSwatchButton(rgba, self._on_palette_color_selected)
            palette_grid.insert(btn, -1)

        sidebar_inner.append(palette_grid)

        # Recent colors
        recent_label = Gtk.Label(label=_("Recent:"))
        recent_label.set_halign(Gtk.Align.START)
        sidebar_inner.append(recent_label)

        self.recent_flow = Gtk.FlowBox()
        self.recent_flow.set_max_children_per_line(10)
        self.recent_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.recent_flow.set_homogeneous(True)
        sidebar_inner.append(self.recent_flow)

        # Drawing area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.drawing_area)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        content_box.append(scrolled)

        # Status bar
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.status_box.add_css_class("toolbar")
        self.status_box.set_margin_start(12)
        self.status_box.set_margin_end(12)
        self.status_box.set_margin_top(2)
        self.status_box.set_margin_bottom(2)

        self.status_tool_label = Gtk.Label(label=_("Tool: Brush"))
        self.status_tool_label.set_halign(Gtk.Align.START)
        self.status_box.append(self.status_tool_label)

        self.status_size_label = Gtk.Label(label=_("Size: {}").format(5))
        self.status_box.append(self.status_size_label)

        self.status_pos_label = Gtk.Label(label=_("Position: {}, {}").format(0, 0))
        self.status_box.append(self.status_pos_label)

        self.status_canvas_label = Gtk.Label(
            label=_("Canvas: {}×{}").format(self.drawing_area.width, self.drawing_area.height))
        self.status_box.append(self.status_canvas_label)

        self.status_zoom_label = Gtk.Label(label="100%")
        self.status_box.append(self.status_zoom_label)

        self.status_file_label = Gtk.Label(label="")
        self.status_file_label.set_hexpand(True)
        self.status_file_label.set_halign(Gtk.Align.END)
        self.status_box.append(self.status_file_label)

        main_box.append(self.status_box)

        # Periodic status update
        GLib.timeout_add(200, self._periodic_status_update)

    def _periodic_status_update(self):
        self.update_status_bar()
        return True

    def update_status_bar(self):
        """Update all status bar elements"""
        if not hasattr(self, 'status_tool_label'):
            return
        da = self.drawing_area
        tool_names = {
            "brush": _("Brush"), "eraser": _("Eraser"), "line": _("Line"),
            "rectangle": _("Rectangle"), "circle": _("Circle"),
            "polygon": _("Polygon"), "star": _("Star"), "fill": _("Fill"),
            "text": _("Text"), "select": _("Selection"),
            "eyedropper": _("Eyedropper"), "spray": _("Spray"),
            "arrow": _("Arrow"), "rounded_rectangle": _("Rounded Rectangle"),
            "crop": _("Crop"), "gradient": _("Gradient"),
        }
        tool_display = tool_names.get(da.tool, da.tool.title())
        self.status_tool_label.set_text(_("Tool: {}").format(tool_display))
        self.status_size_label.set_text(_("Size: {}").format(da.brush_size))
        self.status_pos_label.set_text(
            _("Position: {}, {}").format(int(da.cursor_x), int(da.cursor_y)))
        self.status_canvas_label.set_text(
            _("Canvas: {}×{}").format(da.width, da.height))
        zoom_pct = int(da.zoom_level * 100)
        self.status_zoom_label.set_text(f"{zoom_pct}%")
        if self.current_file:
            self.status_file_label.set_text(os.path.basename(self.current_file))
        else:
            self.status_file_label.set_text("")

        # Update FG/BG indicator
        self.fg_bg_widget.queue_draw()

    def _on_palette_color_selected(self, color_rgba):
        """Handle palette color selection"""
        self.drawing_area.fg_color = color_rgba
        self._add_recent_color(color_rgba)
        self.update_status_bar()

    def _add_recent_color(self, color_rgba):
        """Add color to recent colors list"""
        # Remove if already exists
        if color_rgba in self.drawing_area.recent_colors:
            self.drawing_area.recent_colors.remove(color_rgba)
        self.drawing_area.recent_colors.insert(0, color_rgba)
        # Keep max 10
        self.drawing_area.recent_colors = self.drawing_area.recent_colors[:10]
        self._rebuild_recent_colors()

    def _rebuild_recent_colors(self):
        """Rebuild recent colors flow box"""
        while True:
            child = self.recent_flow.get_child_at_index(0)
            if child is None:
                break
            self.recent_flow.remove(child)
        for c in self.drawing_area.recent_colors:
            btn = ColorSwatchButton(c, self._on_palette_color_selected)
            self.recent_flow.insert(btn, -1)

    def _swap_colors(self):
        da = self.drawing_area
        da.fg_color, da.bg_color = da.bg_color, da.fg_color
        self.fg_bg_widget.queue_draw()

    def on_custom_color(self, button):
        """Open GTK color dialog"""
        dialog = Gtk.ColorDialog()
        dialog.set_with_alpha(True)
        r, g, b, a = self.drawing_area.fg_color
        initial = Gdk.RGBA()
        initial.red = r
        initial.green = g
        initial.blue = b
        initial.alpha = a
        dialog.choose_rgba(self, initial, None, self._on_color_chosen)

    def _on_color_chosen(self, dialog, result):
        try:
            rgba = dialog.choose_rgba_finish(result)
            color = (rgba.red, rgba.green, rgba.blue, rgba.alpha)
            self.drawing_area.fg_color = color
            self._add_recent_color(color)
            self.update_status_bar()
        except GLib.Error:
            pass

    def setup_actions(self):
        """Setup application actions"""
        actions = [
            ("new", self.on_new),
            ("open", self.on_open),
            ("save", self.on_save),
            ("save_as", self.on_save_as),
            ("export", self.on_export),
            ("clear", self.on_clear),
            ("resize_canvas", self.on_resize_canvas),
            ("crop_to_selection", self.on_crop_to_selection),
            ("rotate_90", lambda a, p: self.drawing_area.rotate_canvas(90)),
            ("rotate_180", lambda a, p: self.drawing_area.rotate_canvas(180)),
            ("rotate_270", lambda a, p: self.drawing_area.rotate_canvas(270)),
            ("flip_h", lambda a, p: self.drawing_area.flip_canvas(True)),
            ("flip_v", lambda a, p: self.drawing_area.flip_canvas(False)),
            ("preferences", self.on_preferences),
        ]
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        # Recent files actions
        recent_files = self.settings.get("recent_files", [])
        for i, fpath in enumerate(recent_files[:10]):
            action = Gio.SimpleAction.new(f"open_recent_{i}", None)
            action.connect("activate", self._on_open_recent, fpath)
            self.add_action(action)

    def setup_auto_save(self):
        """Setup auto-save timer based on settings"""
        interval = self.settings.get("auto_save_interval", 0)
        if self.auto_save_id:
            GLib.source_remove(self.auto_save_id)
            self.auto_save_id = None
        if interval > 0 and self.current_file:
            self.auto_save_id = GLib.timeout_add_seconds(
                interval * 60, self._auto_save_tick)

    def _auto_save_tick(self):
        if self.current_file:
            self.drawing_area.save_image(self.current_file)
        return True

    # ─── Tool handlers ───

    def on_tool_changed(self, button, tool_id):
        if button.get_active():
            for tid, btn in self.tool_buttons.items():
                if tid != tool_id:
                    btn.set_active(False)
            self.drawing_area.tool = tool_id
            if tool_id == "text":
                self.show_text_dialog()
            self.update_status_bar()

    def show_text_dialog(self):
        dialog = TextInputDialog(self, self.drawing_area.text_content)
        dialog.connect("response", self.on_text_dialog_response)
        dialog.present()

    def on_text_dialog_response(self, dialog, response):
        if response == "ok":
            self.drawing_area.text_content = dialog.get_text()
            self.drawing_area.font_size = dialog.get_font_size()
        dialog.destroy()

    def on_size_changed(self, scale):
        size = int(scale.get_value())
        self.drawing_area.brush_size = size
        self.update_status_bar()

    def on_opacity_changed(self, scale):
        self.drawing_area.brush_opacity = scale.get_value() / 100.0

    def on_stroke_width_changed(self, scale):
        self.drawing_area.stroke_width = int(scale.get_value())

    def on_fill_mode_changed(self, button, mode):
        if button.get_active():
            self.drawing_area.shape_fill_mode = mode
            # Toggle the other button off
            if mode == "outline":
                self.filled_btn.set_active(False)
            else:
                self.outline_btn.set_active(False)

    def on_brush_shape_changed(self, button, shape_id):
        if button.get_active():
            self.drawing_area.brush_shape = shape_id
            for sid, btn in self.brush_shape_buttons.items():
                if sid != shape_id:
                    btn.set_active(False)

    def on_gradient_mode_changed(self, button, mode):
        if button.get_active():
            self.drawing_area.gradient_mode = mode
            for gid, btn in self.gradient_buttons.items():
                if gid != mode:
                    btn.set_active(False)

    def on_add_layer(self, button):
        self.drawing_area.add_layer()
        self._rebuild_layer_list()

    def on_delete_layer(self, button):
        self.drawing_area.delete_layer()
        self._rebuild_layer_list()

    def on_layer_selected(self, listbox, row):
        if row is not None:
            idx = row.get_index()
            self.drawing_area.set_active_layer(idx)

    def _rebuild_layer_list(self):
        """Rebuild the layer list box"""
        while True:
            row = self.layer_list_box.get_row_at_index(0)
            if row is None:
                break
            self.layer_list_box.remove(row)
        for i, layer in enumerate(self.drawing_area.layers):
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row_box.set_margin_start(4)
            row_box.set_margin_end(4)
            row_box.set_margin_top(2)
            row_box.set_margin_bottom(2)

            vis_btn = Gtk.CheckButton()
            vis_btn.set_active(layer["visible"])
            vis_btn.connect("toggled", self._on_layer_visibility_toggled, i)
            row_box.append(vis_btn)

            label = Gtk.Label(label=layer["name"])
            label.set_hexpand(True)
            label.set_halign(Gtk.Align.START)
            row_box.append(label)

            self.layer_list_box.append(row_box)

        # Select active layer
        active_row = self.layer_list_box.get_row_at_index(self.drawing_area.active_layer_index)
        if active_row:
            self.layer_list_box.select_row(active_row)

    def _on_layer_visibility_toggled(self, button, layer_index):
        if 0 <= layer_index < len(self.drawing_area.layers):
            self.drawing_area.layers[layer_index]["visible"] = button.get_active()
            self.drawing_area.queue_draw()

    # ─── Edit actions ───

    def on_undo(self, action, param):
        if self.drawing_area.undo():
            pass

    def on_redo(self, action, param):
        if self.drawing_area.redo():
            pass

    def on_select_all(self, action, param):
        self.drawing_area.select_all()

    def on_copy(self, action, param):
        self._copy_to_clipboard()

    def on_paste(self, action, param):
        self._paste_from_clipboard()

    def on_cut(self, action, param):
        self._cut_to_clipboard()

    def on_delete_selection(self, action, param):
        self.drawing_area.delete_selection()

    def on_brush_size_up(self, action, param):
        new_size = min(50, self.drawing_area.brush_size + 1)
        self.drawing_area.brush_size = new_size
        self.size_scale.set_value(new_size)

    def on_brush_size_down(self, action, param):
        new_size = max(1, self.drawing_area.brush_size - 1)
        self.drawing_area.brush_size = new_size
        self.size_scale.set_value(new_size)

    def on_reset_colors(self, action, param):
        self.drawing_area.fg_color = (0.0, 0.0, 0.0, 1.0)
        self.drawing_area.bg_color = (1.0, 1.0, 1.0, 1.0)
        self.fg_bg_widget.queue_draw()

    def on_swap_colors(self, action, param):
        self._swap_colors()

    def on_confirm_crop(self, action, param):
        self.drawing_area.confirm_crop()
        self.update_status_bar()

    def on_cancel_crop(self, action, param):
        self.drawing_area.cancel_crop()

    # ─── View actions ───

    def on_zoom_in(self, action, param):
        self.drawing_area.zoom_in()

    def on_zoom_out(self, action, param):
        self.drawing_area.zoom_out()

    def on_zoom_reset(self, action, param):
        self.drawing_area.zoom_reset()

    def on_toggle_grid(self, action, param):
        self.drawing_area.show_grid = not self.drawing_area.show_grid
        self.drawing_area.queue_draw()

    # ─── Canvas actions ───

    def on_clear(self, action, param):
        self.drawing_area.clear_canvas()

    def on_resize_canvas(self, action, param):
        dialog = CanvasResizeDialog(
            self, self.drawing_area.width, self.drawing_area.height)
        dialog.connect("response", self._on_resize_response)
        dialog.present()

    def _on_resize_response(self, dialog, response):
        if response == "ok":
            w, h = dialog.get_dimensions()
            self.drawing_area.resize_canvas(w, h)
            self.update_status_bar()
        dialog.destroy()

    def on_crop_to_selection(self, action, param):
        self.drawing_area.crop_to_selection()
        self.update_status_bar()

    # ─── File actions ───

    def on_new(self, action, param):
        self.drawing_area.clear_canvas()
        self.current_file = None
        self.update_status_bar()

    def on_open(self, action, param):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Open Image"))

        filters = Gio.ListStore.new(Gtk.FileFilter)

        # All images filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name(_("All Images"))
        for fmt_info in OPEN_FORMATS.values():
            for mime in fmt_info[1]:
                all_filter.add_mime_type(mime)
        filters.append(all_filter)

        # Individual format filters
        for fmt_key, fmt_info in OPEN_FORMATS.items():
            f = Gtk.FileFilter()
            f.set_name(_("{} Images").format(fmt_info[0]))
            for mime in fmt_info[1]:
                f.add_mime_type(mime)
            filters.append(f)

        dialog.set_filters(filters)
        dialog.set_default_filter(all_filter)

        # Remember last directory
        last_dir = self.settings.get("last_open_dir", "")
        if last_dir and os.path.isdir(last_dir):
            dialog.set_initial_folder(Gio.File.new_for_path(last_dir))

        dialog.open(self, None, self._on_open_finish)

    def _on_open_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                filename = file.get_path()
                self.drawing_area.load_image(filename)
                self.current_file = filename
                self.settings["last_open_dir"] = os.path.dirname(filename)
                self._add_recent_file(filename)
                self.update_status_bar()
        except GLib.Error:
            pass

    def on_save(self, action, param):
        if self.current_file:
            self.drawing_area.save_image(self.current_file)
            self.update_status_bar()
        else:
            self.on_save_as(action, param)

    def on_save_as(self, action, param):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Save Image"))

        # Default format from settings
        default_fmt = self.settings.get("default_save_format", "png")
        fmt_info = SAVE_FORMATS.get(default_fmt, SAVE_FORMATS["png"])
        dialog.set_initial_name("artwork" + fmt_info[1])

        filters = Gio.ListStore.new(Gtk.FileFilter)
        default_filter = None
        for fmt_key, (name, ext, mime) in SAVE_FORMATS.items():
            f = Gtk.FileFilter()
            f.set_name(_("{} Images").format(name))
            f.add_mime_type(mime)
            filters.append(f)
            if fmt_key == default_fmt:
                default_filter = f

        dialog.set_filters(filters)
        if default_filter:
            dialog.set_default_filter(default_filter)

        # Remember last directory
        last_dir = self.settings.get("last_save_dir", "")
        if last_dir and os.path.isdir(last_dir):
            dialog.set_initial_folder(Gio.File.new_for_path(last_dir))

        dialog.save(self, None, self._on_save_finish)

    def _on_save_finish(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                filename = file.get_path()
                ext = os.path.splitext(filename)[1].lower()

                # If saving as JPEG, ask for quality
                if ext in ('.jpg', '.jpeg'):
                    self._pending_save_filename = filename
                    quality_dialog = JpegQualityDialog(self)
                    quality_dialog.connect("response", self._on_jpeg_quality_response)
                    quality_dialog.present()
                    return

                # Add default extension if none
                if not ext:
                    default_fmt = self.settings.get("default_save_format", "png")
                    filename += SAVE_FORMATS.get(default_fmt, SAVE_FORMATS["png"])[1]

                self.drawing_area.save_image(filename)
                self.current_file = filename
                self.settings["last_save_dir"] = os.path.dirname(filename)
                _save_settings(self.settings)
                self.update_status_bar()
        except GLib.Error:
            pass

    def _on_jpeg_quality_response(self, dialog, response):
        if response == "ok":
            quality = dialog.get_quality()
            self.settings["jpeg_quality"] = quality
            filename = self._pending_save_filename
            self.drawing_area.save_image(filename)
            self.current_file = filename
            self.settings["last_save_dir"] = os.path.dirname(filename)
            _save_settings(self.settings)
            self.update_status_bar()
        dialog.destroy()

    def on_export(self, action, param):
        """Export with custom dimensions"""
        dialog = ExportDialog(
            self, self.drawing_area.width, self.drawing_area.height)
        dialog.connect("response", self._on_export_response)
        dialog.present()

    def _on_export_response(self, dialog, response):
        if response == "ok":
            self._export_width, self._export_height = dialog.get_dimensions()
            dialog.destroy()
            # Now show save dialog
            save_dialog = Gtk.FileDialog()
            save_dialog.set_title(_("Export Image"))
            save_dialog.set_initial_name("export.png")

            filters = Gio.ListStore.new(Gtk.FileFilter)
            for fmt_key, (name, ext, mime) in SAVE_FORMATS.items():
                f = Gtk.FileFilter()
                f.set_name(_("{} Images").format(name))
                f.add_mime_type(mime)
                filters.append(f)
            save_dialog.set_filters(filters)
            save_dialog.save(self, None, self._on_export_save_finish)
        else:
            dialog.destroy()

    def _on_export_save_finish(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                filename = file.get_path()
                ext = os.path.splitext(filename)[1].lower()
                if not ext:
                    filename += ".png"
                self.drawing_area.save_image_with_dimensions(
                    filename, self._export_width, self._export_height)
        except GLib.Error:
            pass

    def on_preferences(self, action, param):
        prefs = PreferencesDialog(self, self.settings)
        prefs.present()

    def _on_open_recent(self, action, param, filepath):
        if os.path.isfile(filepath):
            self.drawing_area.load_image(filepath)
            self.current_file = filepath
            self._add_recent_file(filepath)
            self.update_status_bar()

    def _add_recent_file(self, filepath):
        """Add a file to the recent files list in settings"""
        recent = self.settings.get("recent_files", [])
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.settings["recent_files"] = recent[:10]
        _save_settings(self.settings)

    # ─── Clipboard (Gdk.Clipboard) ───

    def _copy_to_clipboard(self):
        """Copy canvas/selection to system clipboard"""
        da = self.drawing_area
        if da.selection:
            sx, sy, sw, sh = [int(v) for v in da.selection]
            if sw <= 0 or sh <= 0:
                return
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
            ctx = cairo.Context(surf)
            ctx.set_source_surface(da.surface, -sx, -sy)
            ctx.paint()
        else:
            surf = da.flatten_layers()
            sw, sh = da.width, da.height
        # Convert to GdkPixbuf for clipboard
        surf.flush()
        data = bytes(surf.get_data())
        stride = surf.get_stride()
        rgba_data = bytearray(sw * sh * 4)
        for y in range(sh):
            for x in range(sw):
                src_off = y * stride + x * 4
                dst_off = (y * sw + x) * 4
                b_val = data[src_off]
                g_val = data[src_off + 1]
                r_val = data[src_off + 2]
                a_val = data[src_off + 3]
                if a_val > 0:
                    r_val = min(255, r_val * 255 // a_val)
                    g_val = min(255, g_val * 255 // a_val)
                    b_val = min(255, b_val * 255 // a_val)
                rgba_data[dst_off] = r_val
                rgba_data[dst_off + 1] = g_val
                rgba_data[dst_off + 2] = b_val
                rgba_data[dst_off + 3] = a_val
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            bytes(rgba_data), GdkPixbuf.Colorspace.RGB, True, 8,
            sw, sh, sw * 4)
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        clipboard = self.get_clipboard()
        clipboard.set(texture)

    def _paste_from_clipboard(self):
        """Paste from system clipboard as a new layer"""
        clipboard = self.get_clipboard()
        clipboard.read_texture_async(None, self._on_clipboard_texture_ready)

    def _on_clipboard_texture_ready(self, clipboard, result):
        try:
            texture = clipboard.read_texture_finish(result)
            if texture is None:
                return
            tw = texture.get_width()
            th = texture.get_height()
            # Download texture to bytes
            pix_bytes = texture.save_to_png_bytes()
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(pix_bytes.get_data())
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf is None:
                return
            pw = pixbuf.get_width()
            ph = pixbuf.get_height()
            has_alpha = pixbuf.get_has_alpha()
            n_channels = pixbuf.get_n_channels()
            rowstride = pixbuf.get_rowstride()
            pixels = pixbuf.get_pixels()

            # Create a new layer with the pasted content
            da = self.drawing_area
            layer_name = _("Pasted Layer")
            new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, da.width, da.height)
            buf = new_surface.get_data()
            img_stride = new_surface.get_stride()

            for y in range(min(ph, da.height)):
                for x in range(min(pw, da.width)):
                    src_offset = y * rowstride + x * n_channels
                    r = pixels[src_offset]
                    g = pixels[src_offset + 1]
                    b = pixels[src_offset + 2]
                    a = pixels[src_offset + 3] if has_alpha else 255
                    dst_offset = y * img_stride + x * 4
                    buf[dst_offset] = b * a // 255
                    buf[dst_offset + 1] = g * a // 255
                    buf[dst_offset + 2] = r * a // 255
                    buf[dst_offset + 3] = a

            new_surface.mark_dirty()
            insert_idx = da.active_layer_index + 1
            da.layers.insert(insert_idx, {"name": layer_name, "surface": new_surface, "visible": True})
            da.active_layer_index = insert_idx
            da._sync_active_layer()
            self._rebuild_layer_list()
            da.queue_draw()
        except (GLib.Error, Exception):
            pass

    def _cut_to_clipboard(self):
        """Cut selection to clipboard"""
        self._copy_to_clipboard()
        self.drawing_area.cut_selection()


class PaintBrushApp(Adw.Application):
    """Enhanced main application class"""

    def __init__(self):
        super().__init__(application_id="com.danielnylander.paintbrush")
        self.set_flags(Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.settings = _load_settings()

    def do_activate(self):
        window = PaintBrushWindow(self)
        window.present()

        if not self.settings.get("welcome_shown"):
            self._show_welcome(window)

    def _show_welcome(self, win):
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(400)

        page = Adw.StatusPage()
        page.set_icon_name("com.danielnylander.paintbrush")
        page.set_title(_("Welcome to PaintBrush"))
        page.set_description(_("A simple painting app for Linux"))

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content_box.set_halign(Gtk.Align.CENTER)

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        content_box.append(btn)

        # Show recent files if any
        recent_files = self.settings.get("recent_files", [])
        if recent_files:
            recent_label = Gtk.Label(label=_("Recent Files:"))
            recent_label.set_margin_top(12)
            recent_label.add_css_class("heading")
            content_box.append(recent_label)
            for fpath in recent_files[:5]:
                fname = os.path.basename(fpath)
                file_btn = Gtk.Button(label=fname)
                file_btn.set_tooltip_text(fpath)
                file_btn.connect("clicked", self._on_welcome_open_recent, fpath, dialog, win)
                content_box.append(file_btn)

        page.set_child(content_box)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.set_child(box)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()

    def _on_welcome_open_recent(self, btn, filepath, dialog, win):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()
        if os.path.isfile(filepath):
            win.drawing_area.load_image(filepath)
            win.current_file = filepath
            win._add_recent_file(filepath)
            win.update_status_bar()

    def do_startup(self):
        Adw.Application.do_startup(self)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

        # Keyboard accelerators
        self.set_accels_for_action("win.undo", ["<Control>z"])
        self.set_accels_for_action("win.redo", ["<Control><Shift>z"])
        self.set_accels_for_action("win.new", ["<Control>n"])
        self.set_accels_for_action("win.open", ["<Control>o"])
        self.set_accels_for_action("win.save", ["<Control>s"])
        self.set_accels_for_action("win.save_as", ["<Control><Shift>s"])
        self.set_accels_for_action("win.zoom_in", ["<Control>plus", "<Control>equal"])
        self.set_accels_for_action("win.zoom_out", ["<Control>minus"])
        self.set_accels_for_action("win.zoom_reset", ["<Control>0"])
        self.set_accels_for_action("app.quit", ["<Control>q"])

        # Grid and selection
        self.set_accels_for_action("win.toggle_grid", ["<Control>g"])
        self.set_accels_for_action("win.select_all", ["<Control>a"])
        self.set_accels_for_action("win.delete_selection", ["Delete"])
        self.set_accels_for_action("win.copy", ["<Control>c"])
        self.set_accels_for_action("win.paste", ["<Control>v"])
        self.set_accels_for_action("win.cut", ["<Control>x"])

        # Brush size
        self.set_accels_for_action("win.brush_size_down", ["bracketleft"])
        self.set_accels_for_action("win.brush_size_up", ["bracketright"])

        # Color shortcuts
        self.set_accels_for_action("win.reset_colors", ["d"])
        self.set_accels_for_action("win.swap_colors", ["x"])

        # Tool shortcuts
        self.set_accels_for_action("win.tool_brush", ["b"])
        self.set_accels_for_action("win.tool_eraser", ["e"])
        self.set_accels_for_action("win.tool_line", ["l"])
        self.set_accels_for_action("win.tool_rectangle", ["r"])
        self.set_accels_for_action("win.tool_circle", ["c"])
        self.set_accels_for_action("win.tool_text", ["t"])
        self.set_accels_for_action("win.tool_fill", ["f"])
        self.set_accels_for_action("win.tool_star", ["s"])
        self.set_accels_for_action("win.tool_polygon", ["p"])
        self.set_accels_for_action("win.tool_eyedropper", ["i"])
        self.set_accels_for_action("win.tool_select", ["m"])
        self.set_accels_for_action("win.tool_spray", ["a"])
        self.set_accels_for_action("win.tool_arrow", ["w"])
        self.set_accels_for_action("win.tool_rounded_rectangle", ["<Shift>r"])
        self.set_accels_for_action("win.tool_crop", ["<Shift>c"])
        self.set_accels_for_action("win.tool_gradient", ["g"])

        # Rotate shortcut
        self.set_accels_for_action("win.rotate_90", ["<Control>r"])

        # Crop confirm/cancel
        self.set_accels_for_action("win.confirm_crop", ["Return"])
        self.set_accels_for_action("win.cancel_crop", ["Escape"])

    def _on_about(self, action, param):
        about = Adw.AboutDialog()
        about.set_application_name(_("PaintBrush"))
        about.set_application_icon("com.danielnylander.paintbrush")
        about.set_developer_name("Daniel Nylander")
        about.set_version("1.4.0")
        about.set_website("https://github.com/yeager/paintbrush")
        about.set_issue_url("https://github.com/yeager/paintbrush/issues")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_copyright("© 2026 Daniel Nylander")
        about.add_link(_("Help translate"), "https://app.transifex.com/danielnylander/paintbrush")
        about.present(self.get_active_window())

    def _on_quit(self, action, param):
        self.quit()


def main():
    app = PaintBrushApp()
    return app.run([])


if __name__ == "__main__":
    main()
