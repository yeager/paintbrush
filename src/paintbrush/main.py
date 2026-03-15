#!/usr/bin/env python3
"""
PaintBrush - Enhanced mid-level drawing application
Modern GTK4/Adwaita application with Cairo graphics
Version 2.0.0 — professional paint app with full color picker, selections, transforms, filters
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
import colorsys
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

BLEND_MODES = ["normal", "multiply", "screen", "overlay", "darken", "lighten"]

BLEND_MODE_LABELS = {
    "normal": _("Normal"), "multiply": _("Multiply"), "screen": _("Screen"),
    "overlay": _("Overlay"), "darken": _("Darken"), "lighten": _("Lighten"),
}

BLEND_MODE_OPERATORS = {
    "normal": cairo.OPERATOR_OVER,
    "multiply": cairo.OPERATOR_MULTIPLY,
    "screen": cairo.OPERATOR_SCREEN,
    "overlay": cairo.OPERATOR_OVERLAY,
    "darken": cairo.OPERATOR_DARKEN,
    "lighten": cairo.OPERATOR_LIGHTEN,
}

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
        self.selection_type = "rect"  # "rect", "ellipse", "lasso", "color"
        self.selection_points = []  # for lasso
        self.selection_surface = None
        self.selection_dragging = False
        self.selection_offset_x = 0
        self.selection_offset_y = 0
        self.selection_feather = 0
        self.color_select_tolerance = 15

        # Preview surface for shape drawing
        self.preview_surface = None

        # Cursor position tracking
        self.cursor_x = 0
        self.cursor_y = 0

        # Recent colors
        self.recent_colors = []

        # Smooth brush
        self.smooth_brush = True
        self.stroke_points = []

        # Bezier path tool
        self.bezier_points = []  # list of (x, y) anchor points

        # Show rulers
        self.show_rulers = True

        # Pixel grid (auto at >400% zoom)
        self.show_pixel_grid = True

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
        self.layers = [{"name": _("Background"), "surface": self.surface, "visible": True, "opacity": 1.0, "blend_mode": "normal"}]
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

        # Composite all visible layers with blend modes and opacity
        for layer in self.layers:
            if layer["visible"]:
                blend = layer.get("blend_mode", "normal")
                opacity = layer.get("opacity", 1.0)
                op = BLEND_MODE_OPERATORS.get(blend, cairo.OPERATOR_OVER)
                ctx.set_operator(op)
                ctx.set_source_surface(layer["surface"], 0, 0)
                ctx.paint_with_alpha(opacity)
        ctx.set_operator(cairo.OPERATOR_OVER)

        # Draw preview surface (for shape previews)
        if self.preview_surface:
            ctx.set_source_surface(self.preview_surface, 0, 0)
            ctx.paint()

        # Draw grid overlay
        if self.show_grid:
            self._draw_grid(ctx)

        # Draw pixel grid when zoomed in >400%
        if self.show_pixel_grid and self.zoom_level > 4.0:
            self._draw_pixel_grid(ctx)

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

        # Draw selection
        if self.selection:
            sx, sy, sw, sh = self.selection
            ctx.set_dash([4, 4])
            ctx.set_source_rgba(0, 0, 0, 0.8)
            ctx.set_line_width(1)
            if self.selection_type == "ellipse":
                ctx.save()
                ctx.translate(sx + sw / 2, sy + sh / 2)
                ctx.scale(sw / 2, sh / 2)
                ctx.arc(0, 0, 1, 0, 2 * math.pi)
                ctx.restore()
                ctx.stroke()
                ctx.set_dash([4, 4], 4)
                ctx.set_source_rgba(1, 1, 1, 0.8)
                ctx.save()
                ctx.translate(sx + sw / 2, sy + sh / 2)
                ctx.scale(sw / 2, sh / 2)
                ctx.arc(0, 0, 1, 0, 2 * math.pi)
                ctx.restore()
                ctx.stroke()
            elif self.selection_type == "lasso" and self.selection_points:
                ctx.move_to(*self.selection_points[0])
                for pt in self.selection_points[1:]:
                    ctx.line_to(*pt)
                ctx.close_path()
                ctx.stroke()
                ctx.set_dash([4, 4], 4)
                ctx.set_source_rgba(1, 1, 1, 0.8)
                ctx.move_to(*self.selection_points[0])
                for pt in self.selection_points[1:]:
                    ctx.line_to(*pt)
                ctx.close_path()
                ctx.stroke()
            else:
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

        # Draw bezier path preview
        if self.bezier_points:
            ctx.set_dash([3, 3])
            ctx.set_source_rgba(0.2, 0.5, 1.0, 0.8)
            ctx.set_line_width(1)
            ctx.move_to(*self.bezier_points[0])
            for pt in self.bezier_points[1:]:
                ctx.line_to(*pt)
            ctx.stroke()
            ctx.set_dash([])
            for pt in self.bezier_points:
                ctx.arc(pt[0], pt[1], 3, 0, 2 * math.pi)
                ctx.fill()

        # Draw lasso preview during drawing
        if self.tool == "select_lasso" and self.drawing and self.selection_points:
            ctx.set_dash([3, 3])
            ctx.set_source_rgba(0.2, 0.5, 1.0, 0.8)
            ctx.set_line_width(1)
            ctx.move_to(*self.selection_points[0])
            for pt in self.selection_points[1:]:
                ctx.line_to(*pt)
            ctx.stroke()
            ctx.set_dash([])

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

    def _draw_pixel_grid(self, ctx):
        """Draw 1px pixel grid when zoomed in >400%"""
        ctx.set_source_rgba(0.3, 0.3, 0.3, 0.15)
        ctx.set_line_width(0.5 / self.zoom_level)
        for x in range(0, self.width + 1):
            ctx.move_to(x, 0)
            ctx.line_to(x, self.height)
        for y in range(0, self.height + 1):
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
            self.stroke_points = [(start_x, start_y)]

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
        elif self.tool == "bezier":
            self.bezier_points.append((start_x, start_y))
            self.queue_draw()
        elif self.tool == "text":
            self.save_state_for_undo()
            self.draw_text(start_x, start_y)
        elif self.tool == "eyedropper":
            self.pick_color(int(start_x), int(start_y))
        elif self.tool == "select_color":
            self.select_by_color(int(start_x), int(start_y))
        elif self.tool == "select_lasso":
            self.selection_points = [(start_x, start_y)]
        elif self.tool in ["select", "select_ellipse"]:
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
        elif self.tool in ["select", "select_ellipse"]:
            if not self.selection_dragging:
                x1, y1 = self.drag_start_x, self.drag_start_y
                x2, y2 = end_x, end_y
                sx = min(x1, x2)
                sy = min(y1, y2)
                sw = abs(x2 - x1)
                sh = abs(y2 - y1)
                if sw > 2 and sh > 2:
                    self.selection = (sx, sy, sw, sh)
                    self.selection_type = "ellipse" if self.tool == "select_ellipse" else "rect"
            else:
                self.selection_dragging = False
        elif self.tool == "select_lasso":
            if len(self.selection_points) > 2:
                xs = [p[0] for p in self.selection_points]
                ys = [p[1] for p in self.selection_points]
                self.selection = (min(xs), min(ys),
                                  max(xs) - min(xs), max(ys) - min(ys))
                self.selection_type = "lasso"

        self.queue_draw()

    def on_button_press(self, gesture, n_press, x, y):
        """Handle button press for single-click tools"""
        x /= self.zoom_level
        y /= self.zoom_level

        if self.tool in ["brush", "eraser", "fill", "text", "spray", "eyedropper",
                         "select", "select_ellipse", "select_lasso", "select_color",
                         "crop", "gradient"]:
            return

        if self.tool == "bezier" and n_press == 2:
            self.finish_bezier_path()
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
            if self.smooth_brush:
                self.stroke_points.append((current_x, current_y))
                if len(self.stroke_points) > 3:
                    pts = self.stroke_points[-4:]
                    self.draw_smooth_stroke(pts)
                else:
                    self.draw_line_segment(self.last_x, self.last_y, current_x, current_y)
            else:
                self.draw_line_segment(self.last_x, self.last_y, current_x, current_y)
            self.last_x = current_x
            self.last_y = current_y
        elif self.tool == "eraser":
            self.erase_line_segment(self.last_x, self.last_y, current_x, current_y)
            self.last_x = current_x
            self.last_y = current_y
        elif self.tool == "spray":
            self.spray_paint(current_x, current_y)
        elif self.tool == "select_lasso":
            self.selection_points.append((current_x, current_y))
        elif self.tool in ["select", "select_ellipse"] and self.selection_dragging and self.selection:
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
        self.layers.insert(insert_idx, {"name": name, "surface": new_surface, "visible": True, "opacity": 1.0, "blend_mode": "normal"})
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
            new_layers.append({"name": layer["name"], "surface": new_surf, "visible": layer["visible"],
                               "opacity": layer.get("opacity", 1.0), "blend_mode": layer.get("blend_mode", "normal")})
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

    # ─── Selection enhancements ───

    def select_none(self):
        """Deselect all"""
        self.selection = None
        self.selection_surface = None
        self.selection_points = []
        self.queue_draw()

    def invert_selection(self):
        """Invert selection (simplified: swap selected/unselected area)"""
        if not self.selection:
            self.selection = (0, 0, self.width, self.height)
        else:
            self.selection = None
        self.queue_draw()

    def select_by_color(self, x, y):
        """Magic wand / flood select by color with tolerance"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        self.surface.flush()
        buf = self.surface.get_data()
        stride = self.surface.get_stride()
        offset = y * stride + x * 4
        target_b = buf[offset]
        target_g = buf[offset + 1]
        target_r = buf[offset + 2]
        target_a = buf[offset + 3]

        tolerance = self.color_select_tolerance
        min_x, min_y = self.width, self.height
        max_x, max_y = 0, 0
        visited = set()
        stack = [(x, y)]

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if cx < 0 or cx >= self.width or cy < 0 or cy >= self.height:
                continue
            off = cy * stride + cx * 4
            if (abs(buf[off + 2] - target_r) <= tolerance and
                    abs(buf[off + 1] - target_g) <= tolerance and
                    abs(buf[off] - target_b) <= tolerance and
                    abs(buf[off + 3] - target_a) <= tolerance):
                visited.add((cx, cy))
                min_x = min(min_x, cx)
                min_y = min(min_y, cy)
                max_x = max(max_x, cx)
                max_y = max(max_y, cy)
                stack.extend([(cx + 1, cy), (cx - 1, cy),
                              (cx, cy + 1), (cx, cy - 1)])

        if visited:
            self.selection = (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
            self.selection_type = "color"
            self.queue_draw()

    # ─── Smooth brush ───

    def draw_smooth_stroke(self, points):
        """Draw smooth interpolated stroke through points"""
        if len(points) < 2:
            return
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.brush_size)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        if len(points) == 2:
            self.ctx.move_to(*points[0])
            self.ctx.line_to(*points[1])
        else:
            self.ctx.move_to(*points[0])
            for i in range(1, len(points) - 1):
                xc = (points[i][0] + points[i + 1][0]) / 2
                yc = (points[i][1] + points[i + 1][1]) / 2
                self.ctx.curve_to(points[i][0], points[i][1],
                                  points[i][0], points[i][1], xc, yc)
            self.ctx.line_to(*points[-1])
        self.ctx.stroke()
        self.queue_draw()

    # ─── Bezier path tool ───

    def finish_bezier_path(self):
        """Draw the bezier path through collected points"""
        if len(self.bezier_points) < 2:
            self.bezier_points = []
            return
        self.save_state_for_undo()
        r, g, b, a = self.fg_color
        self.ctx.set_source_rgba(r, g, b, a * self.brush_opacity)
        self.ctx.set_line_width(self.stroke_width)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)

        pts = self.bezier_points
        self.ctx.move_to(*pts[0])
        if len(pts) == 2:
            self.ctx.line_to(*pts[1])
        else:
            for i in range(1, len(pts) - 1):
                xc = (pts[i][0] + pts[i + 1][0]) / 2
                yc = (pts[i][1] + pts[i + 1][1]) / 2
                self.ctx.curve_to(pts[i][0], pts[i][1],
                                  pts[i][0], pts[i][1], xc, yc)
            self.ctx.line_to(*pts[-1])
        self.ctx.stroke()
        self.bezier_points = []
        self.queue_draw()

    # ─── Filters ───

    def _get_surface_copy(self, surface):
        """Get a mutable copy of surface pixel data"""
        surface.flush()
        return bytearray(surface.get_data()), surface.get_stride()

    def apply_blur(self, radius=3):
        """Apply box blur (gaussian approximation)"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()
        src = bytes(data)

        # Horizontal pass
        tmp = bytearray(len(src))
        for y in range(h):
            for x in range(w):
                sums = [0, 0, 0, 0]
                count = 0
                for dx in range(-radius, radius + 1):
                    nx = max(0, min(w - 1, x + dx))
                    off = y * stride + nx * 4
                    for c in range(4):
                        sums[c] += src[off + c]
                    count += 1
                off = y * stride + x * 4
                for c in range(4):
                    tmp[off + c] = sums[c] // count

        # Vertical pass
        for y in range(h):
            for x in range(w):
                sums = [0, 0, 0, 0]
                count = 0
                for dy in range(-radius, radius + 1):
                    ny = max(0, min(h - 1, y + dy))
                    off = ny * stride + x * 4
                    for c in range(4):
                        sums[c] += tmp[off + c]
                    count += 1
                off = y * stride + x * 4
                for c in range(4):
                    data[off + c] = sums[c] // count

        self.surface.mark_dirty()
        self.queue_draw()

    def apply_sharpen(self, amount=1.0):
        """Sharpen using unsharp mask"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()
        src = bytes(data)

        # Simple 3x3 sharpen kernel
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                off = y * stride + x * 4
                for c in range(3):
                    center = src[off + c] * (1 + 4 * amount)
                    neighbors = (src[(y - 1) * stride + x * 4 + c] +
                                 src[(y + 1) * stride + x * 4 + c] +
                                 src[y * stride + (x - 1) * 4 + c] +
                                 src[y * stride + (x + 1) * 4 + c])
                    val = int(center - neighbors * amount)
                    data[off + c] = max(0, min(255, val))

        self.surface.mark_dirty()
        self.queue_draw()

    def apply_emboss(self):
        """Apply emboss filter"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()
        src = bytes(data)

        for y in range(1, h - 1):
            for x in range(1, w - 1):
                off = y * stride + x * 4
                for c in range(3):
                    val = (128 +
                           src[(y - 1) * stride + (x - 1) * 4 + c] * -2 +
                           src[(y - 1) * stride + x * 4 + c] * -1 +
                           src[y * stride + (x - 1) * 4 + c] * -1 +
                           src[y * stride + (x + 1) * 4 + c] +
                           src[(y + 1) * stride + x * 4 + c] +
                           src[(y + 1) * stride + (x + 1) * 4 + c] * 2)
                    data[off + c] = max(0, min(255, val))

        self.surface.mark_dirty()
        self.queue_draw()

    def apply_edge_detect(self):
        """Apply Sobel edge detection"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()
        src = bytes(data)

        for y in range(1, h - 1):
            for x in range(1, w - 1):
                off = y * stride + x * 4
                for c in range(3):
                    gx = (-src[(y - 1) * stride + (x - 1) * 4 + c] +
                           src[(y - 1) * stride + (x + 1) * 4 + c] +
                          -2 * src[y * stride + (x - 1) * 4 + c] +
                           2 * src[y * stride + (x + 1) * 4 + c] +
                          -src[(y + 1) * stride + (x - 1) * 4 + c] +
                           src[(y + 1) * stride + (x + 1) * 4 + c])
                    gy = (-src[(y - 1) * stride + (x - 1) * 4 + c] +
                          -2 * src[(y - 1) * stride + x * 4 + c] +
                          -src[(y - 1) * stride + (x + 1) * 4 + c] +
                           src[(y + 1) * stride + (x - 1) * 4 + c] +
                           2 * src[(y + 1) * stride + x * 4 + c] +
                           src[(y + 1) * stride + (x + 1) * 4 + c])
                    val = min(255, int(math.sqrt(gx * gx + gy * gy)))
                    data[off + c] = val
                data[off + 3] = src[off + 3]

        self.surface.mark_dirty()
        self.queue_draw()

    def apply_pixelate(self, block_size=8):
        """Apply pixelate filter"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()
        src = bytes(data)

        for by in range(0, h, block_size):
            for bx in range(0, w, block_size):
                sums = [0, 0, 0, 0]
                count = 0
                for dy in range(min(block_size, h - by)):
                    for dx in range(min(block_size, w - bx)):
                        off = (by + dy) * stride + (bx + dx) * 4
                        for c in range(4):
                            sums[c] += src[off + c]
                        count += 1
                avg = [s // max(1, count) for s in sums]
                for dy in range(min(block_size, h - by)):
                    for dx in range(min(block_size, w - bx)):
                        off = (by + dy) * stride + (bx + dx) * 4
                        for c in range(4):
                            data[off + c] = avg[c]

        self.surface.mark_dirty()
        self.queue_draw()

    def apply_noise(self, amount=30):
        """Add random noise"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()

        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                if data[off + 3] > 0:
                    for c in range(3):
                        noise = random.randint(-amount, amount)
                        data[off + c] = max(0, min(255, data[off + c] + noise))

        self.surface.mark_dirty()
        self.queue_draw()

    # ─── Image adjustments ───

    def adjust_brightness_contrast(self, brightness=0, contrast=0):
        """Adjust brightness (-100..100) and contrast (-100..100)"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()

        factor = (259 * (contrast + 255)) / (255 * (259 - contrast))
        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                a = data[off + 3]
                if a == 0:
                    continue
                for c in range(3):
                    # Unpremultiply
                    val = min(255, data[off + c] * 255 // a) if a > 0 else 0
                    val = int(factor * (val - 128) + 128 + brightness)
                    val = max(0, min(255, val))
                    data[off + c] = val * a // 255

        self.surface.mark_dirty()
        self.queue_draw()

    def adjust_hue_saturation(self, hue_shift=0, saturation=0):
        """Adjust hue (degrees) and saturation (-100..100)"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()
        hue_shift_norm = hue_shift / 360.0
        sat_factor = 1.0 + saturation / 100.0

        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                a = data[off + 3]
                if a == 0:
                    continue
                b_val = min(255, data[off] * 255 // a) if a > 0 else 0
                g_val = min(255, data[off + 1] * 255 // a) if a > 0 else 0
                r_val = min(255, data[off + 2] * 255 // a) if a > 0 else 0
                h_v, s_v, v_v = colorsys.rgb_to_hsv(r_val / 255.0, g_val / 255.0, b_val / 255.0)
                h_v = (h_v + hue_shift_norm) % 1.0
                s_v = max(0.0, min(1.0, s_v * sat_factor))
                r_n, g_n, b_n = colorsys.hsv_to_rgb(h_v, s_v, v_v)
                data[off + 2] = int(r_n * 255) * a // 255
                data[off + 1] = int(g_n * 255) * a // 255
                data[off] = int(b_n * 255) * a // 255

        self.surface.mark_dirty()
        self.queue_draw()

    def apply_curves(self, lut):
        """Apply a 256-entry lookup table to RGB channels"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()

        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                a = data[off + 3]
                if a == 0:
                    continue
                for c in range(3):
                    val = min(255, data[off + c] * 255 // a) if a > 0 else 0
                    val = lut[val]
                    data[off + c] = val * a // 255

        self.surface.mark_dirty()
        self.queue_draw()

    def convert_grayscale(self):
        """Convert to grayscale"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()

        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                a = data[off + 3]
                if a == 0:
                    continue
                b_v = data[off]
                g_v = data[off + 1]
                r_v = data[off + 2]
                gray = int(0.299 * r_v + 0.587 * g_v + 0.114 * b_v)
                data[off] = gray
                data[off + 1] = gray
                data[off + 2] = gray

        self.surface.mark_dirty()
        self.queue_draw()

    def invert_colors(self):
        """Invert all colors"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()

        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                a = data[off + 3]
                if a == 0:
                    continue
                data[off] = a - data[off]
                data[off + 1] = a - data[off + 1]
                data[off + 2] = a - data[off + 2]

        self.surface.mark_dirty()
        self.queue_draw()

    def auto_levels(self):
        """Auto-adjust levels by stretching histogram"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        stride = self.surface.get_stride()
        data = self.surface.get_data()

        min_v = 255
        max_v = 0
        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                if data[off + 3] == 0:
                    continue
                for c in range(3):
                    v = data[off + c]
                    min_v = min(min_v, v)
                    max_v = max(max_v, v)

        if max_v <= min_v:
            return
        scale = 255.0 / (max_v - min_v)
        for y in range(h):
            for x in range(w):
                off = y * stride + x * 4
                if data[off + 3] == 0:
                    continue
                for c in range(3):
                    data[off + c] = max(0, min(255, int((data[off + c] - min_v) * scale)))

        self.surface.mark_dirty()
        self.queue_draw()

    # ─── Transform methods ───

    def scale_canvas(self, new_w, new_h):
        """Scale entire canvas to new dimensions"""
        self.save_state_for_undo()
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, new_w, new_h)
        ctx = cairo.Context(new_surface)
        self._apply_antialiasing(ctx)
        ctx.scale(new_w / self.width, new_h / self.height)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()
        self.width = new_w
        self.height = new_h
        self.surface = new_surface
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)
        # Update layers
        new_layers = []
        for layer in self.layers:
            ns = cairo.ImageSurface(cairo.FORMAT_ARGB32, new_w, new_h)
            c = cairo.Context(ns)
            c.scale(new_w / max(1, layer["surface"].get_width()),
                    new_h / max(1, layer["surface"].get_height()))
            c.set_source_surface(layer["surface"], 0, 0)
            c.paint()
            new_layers.append({"name": layer["name"], "surface": ns,
                               "visible": layer["visible"],
                               "opacity": layer.get("opacity", 1.0),
                               "blend_mode": layer.get("blend_mode", "normal")})
        self.layers = new_layers
        self._sync_active_layer()
        self.set_size_request(self.width, self.height)
        self.undo_manager.save_state(self.surface)
        self.queue_draw()

    def shear_canvas(self, shear_x=0.0, shear_y=0.0):
        """Shear canvas by factors"""
        self.save_state_for_undo()
        new_w = int(self.width + abs(shear_x) * self.height)
        new_h = int(self.height + abs(shear_y) * self.width)
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, new_w, new_h)
        ctx = cairo.Context(new_surface)
        self._apply_antialiasing(ctx)
        matrix = cairo.Matrix(1, shear_y, shear_x, 1,
                              max(0, -shear_x * self.height),
                              max(0, -shear_y * self.width))
        ctx.set_matrix(matrix)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()
        self.width = new_w
        self.height = new_h
        self.surface = new_surface
        self.ctx = cairo.Context(self.surface)
        self._apply_antialiasing(self.ctx)
        self.layers[self.active_layer_index]["surface"] = self.surface
        self.set_size_request(self.width, self.height)
        self.undo_manager.save_state(self.surface)
        self.queue_draw()

    def perspective_transform(self, top_squeeze=0.0, bottom_squeeze=0.0):
        """Simple perspective by scaling rows"""
        self.save_state_for_undo()
        self.surface.flush()
        w, h = self.width, self.height
        src_data = bytes(self.surface.get_data())
        src_stride = self.surface.get_stride()
        new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        dst_data = new_surface.get_data()
        dst_stride = new_surface.get_stride()

        for y in range(h):
            t = y / max(1, h - 1)
            squeeze = top_squeeze * (1 - t) + bottom_squeeze * t
            row_w = max(1, w - int(abs(squeeze) * w))
            offset_x = (w - row_w) // 2
            for x in range(w):
                src_x = int((x - offset_x) * w / max(1, row_w))
                src_x = max(0, min(w - 1, src_x))
                s_off = y * src_stride + src_x * 4
                d_off = y * dst_stride + x * 4
                for c in range(4):
                    dst_data[d_off + c] = src_data[s_off + c]

        new_surface.mark_dirty()
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.ctx.set_source_surface(new_surface, 0, 0)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
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


class AdjustmentDialog(Adw.MessageDialog):
    """Generic dialog for image adjustments with sliders"""

    def __init__(self, parent, title, sliders):
        super().__init__(transient_for=parent)
        self.set_heading(title)
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Apply"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        self.sliders = {}
        grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        for i, (name, label, min_v, max_v, default) in enumerate(sliders):
            grid.attach(Gtk.Label(label=label), 0, i, 1, 1)
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_v, max_v, 1)
            scale.set_value(default)
            scale.set_size_request(250, -1)
            scale.set_hexpand(True)
            grid.attach(scale, 1, i, 1, 1)
            self.sliders[name] = scale

        self.set_extra_child(grid)

    def get_value(self, name):
        return self.sliders[name].get_value()


class ColorCurvesDialog(Adw.MessageDialog):
    """Simple color curves with control points"""

    def __init__(self, parent):
        super().__init__(transient_for=parent)
        self.set_heading(_("Color Curves"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Apply"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        self.points = [(0, 0), (64, 64), (128, 128), (192, 192), (255, 255)]
        self.selected_point = -1

        self.curve_area = Gtk.DrawingArea()
        self.curve_area.set_size_request(256, 256)
        self.curve_area.set_draw_func(self._draw_curve)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_click)
        self.curve_area.add_controller(click)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        self.curve_area.add_controller(drag)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(Gtk.Label(label=_("Click and drag points to adjust")))
        box.append(self.curve_area)
        self.set_extra_child(box)

    def _draw_curve(self, area, ctx, w, h, data=None):
        # Background
        ctx.set_source_rgb(0.15, 0.15, 0.15)
        ctx.paint()
        # Grid
        ctx.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        ctx.set_line_width(0.5)
        for i in range(1, 4):
            v = i * w / 4
            ctx.move_to(v, 0)
            ctx.line_to(v, h)
            ctx.move_to(0, v)
            ctx.line_to(w, v)
        ctx.stroke()
        # Identity line
        ctx.set_source_rgba(0.4, 0.4, 0.4, 0.5)
        ctx.move_to(0, h)
        ctx.line_to(w, 0)
        ctx.stroke()
        # Curve
        lut = self.generate_lut()
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(1.5)
        for i in range(256):
            x = i * w / 255
            y = h - lut[i] * h / 255
            if i == 0:
                ctx.move_to(x, y)
            else:
                ctx.line_to(x, y)
        ctx.stroke()
        # Control points
        for px, py in self.points:
            x = px * w / 255
            y = h - py * h / 255
            ctx.set_source_rgb(1, 0.5, 0)
            ctx.arc(x, y, 5, 0, 2 * math.pi)
            ctx.fill()

    def _on_click(self, gesture, n_press, x, y):
        w = self.curve_area.get_width()
        h = self.curve_area.get_height()
        px = int(x * 255 / max(1, w))
        py = int((h - y) * 255 / max(1, h))
        px = max(0, min(255, px))
        py = max(0, min(255, py))
        # Find nearest point
        for i, (ppx, ppy) in enumerate(self.points):
            if abs(ppx - px) < 15 and abs(ppy - py) < 15:
                self.selected_point = i
                return
        # Add new point
        self.points.append((px, py))
        self.points.sort(key=lambda p: p[0])
        self.curve_area.queue_draw()

    def _on_drag_begin(self, gesture, x, y):
        w = self.curve_area.get_width()
        h = self.curve_area.get_height()
        px = int(x * 255 / max(1, w))
        py = int((h - y) * 255 / max(1, h))
        for i, (ppx, ppy) in enumerate(self.points):
            if abs(ppx - px) < 15 and abs(ppy - py) < 15:
                self.selected_point = i
                return
        self.selected_point = -1

    def _on_drag_update(self, gesture, ox, oy):
        if self.selected_point < 0:
            return
        _, sx, sy = gesture.get_start_point()
        w = self.curve_area.get_width()
        h = self.curve_area.get_height()
        px = int((sx + ox) * 255 / max(1, w))
        py = int((h - sy - oy) * 255 / max(1, h))
        px = max(0, min(255, px))
        py = max(0, min(255, py))
        i = self.selected_point
        if i == 0:
            px = 0
        elif i == len(self.points) - 1:
            px = 255
        self.points[i] = (px, py)
        self.curve_area.queue_draw()

    def generate_lut(self):
        """Generate 256-entry lookup table from control points"""
        lut = [0] * 256
        pts = sorted(self.points, key=lambda p: p[0])
        for i in range(256):
            # Find surrounding points
            p1 = pts[0]
            p2 = pts[-1]
            for j in range(len(pts) - 1):
                if pts[j][0] <= i <= pts[j + 1][0]:
                    p1 = pts[j]
                    p2 = pts[j + 1]
                    break
            if p2[0] == p1[0]:
                lut[i] = p1[1]
            else:
                t = (i - p1[0]) / (p2[0] - p1[0])
                lut[i] = max(0, min(255, int(p1[1] + t * (p2[1] - p1[1]))))
        return lut


class ScaleDialog(Adw.MessageDialog):
    """Dialog for scaling canvas/selection"""

    def __init__(self, parent, current_width, current_height):
        super().__init__(transient_for=parent)
        self.set_heading(_("Scale"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Scale"))
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

        self.lock_check = Gtk.CheckButton(label=_("Lock aspect ratio"))
        self.lock_check.set_active(True)
        grid.attach(self.lock_check, 0, 2, 2, 1)

        self.width_spin.connect("value-changed", self._on_width_changed)
        self.height_spin.connect("value-changed", self._on_height_changed)
        self.set_extra_child(grid)

    def _on_width_changed(self, spin):
        if self._updating or not self.lock_check.get_active():
            return
        self._updating = True
        self.height_spin.set_value(max(1, int(spin.get_value() / self._aspect_ratio)))
        self._updating = False

    def _on_height_changed(self, spin):
        if self._updating or not self.lock_check.get_active():
            return
        self._updating = True
        self.width_spin.set_value(max(1, int(spin.get_value() * self._aspect_ratio)))
        self._updating = False

    def get_dimensions(self):
        return int(self.width_spin.get_value()), int(self.height_spin.get_value())


class ShearDialog(Adw.MessageDialog):
    """Dialog for shear transform"""

    def __init__(self, parent):
        super().__init__(transient_for=parent)
        self.set_heading(_("Shear"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Apply"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        grid.attach(Gtk.Label(label=_("Horizontal:")), 0, 0, 1, 1)
        self.shear_x = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.05)
        self.shear_x.set_value(0)
        self.shear_x.set_size_request(200, -1)
        grid.attach(self.shear_x, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label=_("Vertical:")), 0, 1, 1, 1)
        self.shear_y = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.05)
        self.shear_y.set_value(0)
        self.shear_y.set_size_request(200, -1)
        grid.attach(self.shear_y, 1, 1, 1, 1)

        self.set_extra_child(grid)


class PerspectiveDialog(Adw.MessageDialog):
    """Dialog for perspective transform"""

    def __init__(self, parent):
        super().__init__(transient_for=parent)
        self.set_heading(_("Perspective"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("Apply"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        grid.attach(Gtk.Label(label=_("Top squeeze:")), 0, 0, 1, 1)
        self.top_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -0.5, 0.5, 0.01)
        self.top_scale.set_value(0)
        self.top_scale.set_size_request(200, -1)
        grid.attach(self.top_scale, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label=_("Bottom squeeze:")), 0, 1, 1, 1)
        self.bottom_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -0.5, 0.5, 0.01)
        self.bottom_scale.set_value(0)
        self.bottom_scale.set_size_request(200, -1)
        grid.attach(self.bottom_scale, 1, 1, 1, 1)

        self.set_extra_child(grid)


class HSVColorWidget(Gtk.Box):
    """HSV color picker with sat/val square and hue slider"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.hue = 0.0
        self.saturation = 1.0
        self.value = 1.0
        self.alpha = 1.0
        self._cached_hue = -1
        self._cached_surface = None
        self.on_color_changed = None

        # Saturation/Value square
        self.sv_area = Gtk.DrawingArea()
        self.sv_area.set_size_request(180, 120)
        self.sv_area.set_draw_func(self._draw_sv)
        sv_click = Gtk.GestureClick()
        sv_click.connect("pressed", self._sv_click)
        self.sv_area.add_controller(sv_click)
        sv_drag = Gtk.GestureDrag()
        sv_drag.connect("drag-begin", self._sv_drag_begin)
        sv_drag.connect("drag-update", self._sv_drag_update)
        self.sv_area.add_controller(sv_drag)
        self.append(self.sv_area)

        # Hue slider
        hue_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        hue_box.append(Gtk.Label(label=_("H:")))
        self.hue_area = Gtk.DrawingArea()
        self.hue_area.set_size_request(150, 18)
        self.hue_area.set_hexpand(True)
        self.hue_area.set_draw_func(self._draw_hue)
        hue_click = Gtk.GestureClick()
        hue_click.connect("pressed", self._hue_click)
        self.hue_area.add_controller(hue_click)
        hue_drag = Gtk.GestureDrag()
        hue_drag.connect("drag-begin", self._hue_drag_begin)
        hue_drag.connect("drag-update", self._hue_drag_update)
        self.hue_area.add_controller(hue_drag)
        hue_box.append(self.hue_area)
        self.append(hue_box)

        # Alpha slider
        alpha_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        alpha_box.append(Gtk.Label(label=_("A:")))
        self.alpha_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.alpha_scale.set_value(100)
        self.alpha_scale.set_hexpand(True)
        self.alpha_scale.connect("value-changed", self._on_alpha_changed)
        alpha_box.append(self.alpha_scale)
        self.append(alpha_box)

        # RGB entries
        rgb_grid = Gtk.Grid(column_spacing=4, row_spacing=2)
        self.r_spin = Gtk.SpinButton.new_with_range(0, 255, 1)
        self.g_spin = Gtk.SpinButton.new_with_range(0, 255, 1)
        self.b_spin = Gtk.SpinButton.new_with_range(0, 255, 1)
        for i, (label, spin) in enumerate([(_("R:"), self.r_spin), (_("G:"), self.g_spin), (_("B:"), self.b_spin)]):
            rgb_grid.attach(Gtk.Label(label=label), i * 2, 0, 1, 1)
            spin.set_size_request(60, -1)
            spin.connect("value-changed", self._on_rgb_changed)
            rgb_grid.attach(spin, i * 2 + 1, 0, 1, 1)
        self.append(rgb_grid)

        # Hex entry
        hex_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        hex_box.append(Gtk.Label(label=_("Hex:")))
        self.hex_entry = Gtk.Entry()
        self.hex_entry.set_max_length(7)
        self.hex_entry.set_text("#000000")
        self.hex_entry.set_hexpand(True)
        self.hex_entry.connect("activate", self._on_hex_activate)
        hex_box.append(self.hex_entry)
        self.append(hex_box)

        self._updating = False
        self._sync_rgb_from_hsv()

    def _rebuild_sv_cache(self, w, h):
        self._cached_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        buf = self._cached_surface.get_data()
        stride = self._cached_surface.get_stride()
        for y in range(h):
            for x in range(w):
                s = x / max(1, w - 1)
                v = 1.0 - y / max(1, h - 1)
                r, g, b = colorsys.hsv_to_rgb(self.hue, s, v)
                off = y * stride + x * 4
                buf[off] = int(b * 255)
                buf[off + 1] = int(g * 255)
                buf[off + 2] = int(r * 255)
                buf[off + 3] = 255
        self._cached_surface.mark_dirty()
        self._cached_hue = self.hue

    def _draw_sv(self, area, ctx, w, h, data=None):
        if self._cached_hue != self.hue or self._cached_surface is None:
            self._rebuild_sv_cache(w, h)
        ctx.set_source_surface(self._cached_surface, 0, 0)
        ctx.paint()
        cx = self.saturation * (w - 1)
        cy = (1.0 - self.value) * (h - 1)
        ctx.set_line_width(1.5)
        ctx.set_source_rgb(1 if self.value < 0.5 else 0,
                           1 if self.value < 0.5 else 0,
                           1 if self.value < 0.5 else 0)
        ctx.arc(cx, cy, 5, 0, 2 * math.pi)
        ctx.stroke()

    def _draw_hue(self, area, ctx, w, h, data=None):
        for x in range(w):
            hu = x / max(1, w - 1)
            r, g, b = colorsys.hsv_to_rgb(hu, 1, 1)
            ctx.set_source_rgb(r, g, b)
            ctx.rectangle(x, 0, 1, h)
            ctx.fill()
        mx = self.hue * (w - 1)
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(2)
        ctx.rectangle(mx - 1, 0, 3, h)
        ctx.stroke()

    def _pick_sv(self, x, y):
        w = self.sv_area.get_width()
        h = self.sv_area.get_height()
        self.saturation = max(0, min(1, x / max(1, w - 1)))
        self.value = max(0, min(1, 1.0 - y / max(1, h - 1)))
        self._sync_rgb_from_hsv()
        self.sv_area.queue_draw()

    def _sv_click(self, gesture, n, x, y):
        self._pick_sv(x, y)

    def _sv_drag_begin(self, gesture, x, y):
        self._pick_sv(x, y)

    def _sv_drag_update(self, gesture, ox, oy):
        _, sx, sy = gesture.get_start_point()
        self._pick_sv(sx + ox, sy + oy)

    def _pick_hue(self, x):
        w = self.hue_area.get_width()
        self.hue = max(0, min(1, x / max(1, w - 1)))
        self._cached_hue = -1
        self._sync_rgb_from_hsv()
        self.sv_area.queue_draw()
        self.hue_area.queue_draw()

    def _hue_click(self, gesture, n, x, y):
        self._pick_hue(x)

    def _hue_drag_begin(self, gesture, x, y):
        self._pick_hue(x)

    def _hue_drag_update(self, gesture, ox, oy):
        _, sx, sy = gesture.get_start_point()
        self._pick_hue(sx + ox)

    def _on_alpha_changed(self, scale):
        self.alpha = scale.get_value() / 100.0
        if self.on_color_changed and not self._updating:
            self.on_color_changed(self.get_rgba())

    def _sync_rgb_from_hsv(self):
        self._updating = True
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.saturation, self.value)
        self.r_spin.set_value(int(r * 255))
        self.g_spin.set_value(int(g * 255))
        self.b_spin.set_value(int(b * 255))
        self.hex_entry.set_text("#{:02x}{:02x}{:02x}".format(
            int(r * 255), int(g * 255), int(b * 255)))
        self._updating = False
        if self.on_color_changed:
            self.on_color_changed(self.get_rgba())

    def _on_rgb_changed(self, spin):
        if self._updating:
            return
        r = self.r_spin.get_value() / 255.0
        g = self.g_spin.get_value() / 255.0
        b = self.b_spin.get_value() / 255.0
        self.hue, self.saturation, self.value = colorsys.rgb_to_hsv(r, g, b)
        self._cached_hue = -1
        self._updating = True
        self.hex_entry.set_text("#{:02x}{:02x}{:02x}".format(
            int(r * 255), int(g * 255), int(b * 255)))
        self._updating = False
        self.sv_area.queue_draw()
        self.hue_area.queue_draw()
        if self.on_color_changed:
            self.on_color_changed(self.get_rgba())

    def _on_hex_activate(self, entry):
        text = entry.get_text().strip().lstrip('#')
        if len(text) == 6:
            try:
                r = int(text[0:2], 16)
                g = int(text[2:4], 16)
                b = int(text[4:6], 16)
                self._updating = True
                self.r_spin.set_value(r)
                self.g_spin.set_value(g)
                self.b_spin.set_value(b)
                self._updating = False
                self.hue, self.saturation, self.value = colorsys.rgb_to_hsv(
                    r / 255.0, g / 255.0, b / 255.0)
                self._cached_hue = -1
                self.sv_area.queue_draw()
                self.hue_area.queue_draw()
                if self.on_color_changed:
                    self.on_color_changed(self.get_rgba())
            except ValueError:
                pass

    def get_rgba(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.saturation, self.value)
        return (r, g, b, self.alpha)

    def set_rgba(self, rgba):
        r, g, b = rgba[0], rgba[1], rgba[2]
        self.alpha = rgba[3] if len(rgba) > 3 else 1.0
        self.hue, self.saturation, self.value = colorsys.rgb_to_hsv(r, g, b)
        self._cached_hue = -1
        self._updating = True
        self.r_spin.set_value(int(r * 255))
        self.g_spin.set_value(int(g * 255))
        self.b_spin.set_value(int(b * 255))
        self.hex_entry.set_text("#{:02x}{:02x}{:02x}".format(
            int(r * 255), int(g * 255), int(b * 255)))
        self.alpha_scale.set_value(self.alpha * 100)
        self._updating = False
        self.sv_area.queue_draw()
        self.hue_area.queue_draw()


class RulerWidget(Gtk.DrawingArea):
    """Ruler widget for top or left of canvas"""

    def __init__(self, orientation="horizontal"):
        super().__init__()
        self.orientation = orientation
        self.zoom = 1.0
        self.scroll_offset = 0
        if orientation == "horizontal":
            self.set_size_request(-1, 20)
        else:
            self.set_size_request(20, -1)
        self.set_draw_func(self._draw)

    def _draw(self, area, ctx, w, h, data=None):
        ctx.set_source_rgb(0.9, 0.9, 0.9)
        ctx.paint()
        ctx.set_source_rgb(0.3, 0.3, 0.3)
        ctx.set_line_width(0.5)
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(8)

        step = max(10, int(50 / self.zoom))
        step = round(step / 10) * 10 or 10

        if self.orientation == "horizontal":
            for px in range(0, int(w / self.zoom) + step, step):
                x = px * self.zoom - self.scroll_offset
                if 0 <= x <= w:
                    ctx.move_to(x, h - 5)
                    ctx.line_to(x, h)
                    ctx.stroke()
                    ctx.move_to(x + 2, h - 7)
                    ctx.show_text(str(px))
        else:
            for py in range(0, int(h / self.zoom) + step, step):
                y = py * self.zoom - self.scroll_offset
                if 0 <= y <= h:
                    ctx.move_to(w - 5, y)
                    ctx.line_to(w, y)
                    ctx.stroke()
                    ctx.save()
                    ctx.move_to(2, y + 10)
                    ctx.show_text(str(py))
                    ctx.restore()

    def update_zoom(self, zoom, offset=0):
        self.zoom = zoom
        self.scroll_offset = offset
        self.queue_draw()


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
    """Professional main window with full feature set"""

    def __init__(self, app):
        super().__init__(application=app)

        self.settings = app.settings
        self.set_title(_("PaintBrush"))
        self.set_default_size(1280, 800)

        self.current_file = None
        self.auto_save_id = None
        self._is_fullscreen = False

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
            "tool_select_ellipse": "select_ellipse",
            "tool_select_lasso": "select_lasso",
            "tool_select_color": "select_color",
            "tool_eyedropper": "eyedropper",
            "tool_spray": "spray",
            "tool_arrow": "arrow",
            "tool_rounded_rectangle": "rounded_rectangle",
            "tool_crop": "crop",
            "tool_gradient": "gradient",
            "tool_bezier": "bezier",
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
        """Create the professional user interface"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # App menu button (hamburger)
        app_menu_btn = Gtk.MenuButton()
        app_menu_btn.set_icon_name("open-menu-symbolic")
        app_menu = Gio.Menu()
        app_section = Gio.Menu()
        app_section.append(_("Preferences"), "win.preferences")
        app_section.append(_("Keyboard Shortcuts"), "win.show-shortcuts")
        app_section.append(_("About PaintBrush"), "app.about")
        app_section.append(_("Quit"), "app.quit")
        app_menu.append_section(None, app_section)
        app_menu_btn.set_menu_model(app_menu)
        header.pack_end(app_menu_btn)

        # ─── Menubar ───
        menubar_model = Gio.Menu()

        # File menu
        file_menu = Gio.Menu()
        file_ops = Gio.Menu()
        file_ops.append(_("New"), "win.new")
        file_ops.append(_("Open"), "win.open")
        file_ops.append(_("Save"), "win.save")
        file_ops.append(_("Save As"), "win.save_as")
        file_ops.append(_("Export…"), "win.export")
        file_menu.append_section(None, file_ops)
        self.recent_menu = Gio.Menu()
        recent_files = self.settings.get("recent_files", [])
        for i, fpath in enumerate(recent_files[:10]):
            self.recent_menu.append(os.path.basename(fpath), f"win.open_recent_{i}")
        if recent_files:
            file_menu.append_submenu(_("Recent Files"), self.recent_menu)
        menubar_model.append_submenu(_("File"), file_menu)

        # Edit menu
        edit_menu = Gio.Menu()
        edit_ops = Gio.Menu()
        edit_ops.append(_("Undo"), "win.undo")
        edit_ops.append(_("Redo"), "win.redo")
        edit_menu.append_section(None, edit_ops)
        clipboard_ops = Gio.Menu()
        clipboard_ops.append(_("Copy"), "win.copy")
        clipboard_ops.append(_("Paste"), "win.paste")
        clipboard_ops.append(_("Cut"), "win.cut")
        edit_menu.append_section(None, clipboard_ops)
        canvas_ops = Gio.Menu()
        canvas_ops.append(_("Clear Canvas"), "win.clear")
        canvas_ops.append(_("Resize Canvas…"), "win.resize_canvas")
        edit_menu.append_section(None, canvas_ops)
        menubar_model.append_submenu(_("Edit"), edit_menu)

        # Image menu
        image_menu = Gio.Menu()
        transform_ops = Gio.Menu()
        transform_ops.append(_("Rotate 90°"), "win.rotate_90")
        transform_ops.append(_("Rotate 180°"), "win.rotate_180")
        transform_ops.append(_("Rotate 270°"), "win.rotate_270")
        transform_ops.append(_("Flip Horizontal"), "win.flip_h")
        transform_ops.append(_("Flip Vertical"), "win.flip_v")
        image_menu.append_section(None, transform_ops)
        scale_ops = Gio.Menu()
        scale_ops.append(_("Scale…"), "win.scale_canvas")
        scale_ops.append(_("Shear…"), "win.shear_canvas")
        scale_ops.append(_("Perspective…"), "win.perspective_canvas")
        scale_ops.append(_("Crop to Selection"), "win.crop_to_selection")
        image_menu.append_section(None, scale_ops)
        menubar_model.append_submenu(_("Image"), image_menu)

        # Layer menu
        layer_menu = Gio.Menu()
        layer_ops = Gio.Menu()
        layer_ops.append(_("Add Layer"), "win.add_layer")
        layer_ops.append(_("Delete Layer"), "win.delete_layer")
        layer_ops.append(_("Flatten Image"), "win.flatten_image")
        layer_menu.append_section(None, layer_ops)
        menubar_model.append_submenu(_("Layer"), layer_menu)

        # Colors menu
        colors_menu = Gio.Menu()
        adjust_ops = Gio.Menu()
        adjust_ops.append(_("Brightness/Contrast…"), "win.brightness_contrast")
        adjust_ops.append(_("Hue/Saturation…"), "win.hue_saturation")
        adjust_ops.append(_("Color Curves…"), "win.color_curves")
        colors_menu.append_section(None, adjust_ops)
        color_ops = Gio.Menu()
        color_ops.append(_("Grayscale"), "win.grayscale")
        color_ops.append(_("Invert Colors"), "win.invert_colors")
        color_ops.append(_("Auto Levels"), "win.auto_levels")
        colors_menu.append_section(None, color_ops)
        menubar_model.append_submenu(_("Colors"), colors_menu)

        # Filters menu
        filters_menu = Gio.Menu()
        filter_ops = Gio.Menu()
        filter_ops.append(_("Blur…"), "win.filter_blur")
        filter_ops.append(_("Sharpen…"), "win.filter_sharpen")
        filter_ops.append(_("Emboss"), "win.filter_emboss")
        filter_ops.append(_("Edge Detect"), "win.filter_edge_detect")
        filter_ops.append(_("Pixelate…"), "win.filter_pixelate")
        filter_ops.append(_("Noise…"), "win.filter_noise")
        filters_menu.append_section(None, filter_ops)
        menubar_model.append_submenu(_("Filters"), filters_menu)

        # Select menu
        select_menu = Gio.Menu()
        select_ops = Gio.Menu()
        select_ops.append(_("Select All"), "win.select_all")
        select_ops.append(_("Select None"), "win.select_none")
        select_ops.append(_("Invert Selection"), "win.invert_selection")
        select_ops.append(_("Delete Selection"), "win.delete_selection")
        select_menu.append_section(None, select_ops)
        menubar_model.append_submenu(_("Select"), select_menu)

        # View menu
        view_menu = Gio.Menu()
        view_ops = Gio.Menu()
        view_ops.append(_("Zoom In"), "win.zoom_in")
        view_ops.append(_("Zoom Out"), "win.zoom_out")
        view_ops.append(_("Zoom Reset"), "win.zoom_reset")
        view_ops.append(_("Fit to Window"), "win.fit_to_window")
        view_menu.append_section(None, view_ops)
        toggle_ops = Gio.Menu()
        toggle_ops.append(_("Toggle Grid"), "win.toggle_grid")
        toggle_ops.append(_("Toggle Rulers"), "win.toggle_rulers")
        toggle_ops.append(_("Fullscreen"), "win.toggle_fullscreen")
        view_menu.append_section(None, toggle_ops)
        menubar_model.append_submenu(_("View"), view_menu)

        menubar = Gtk.PopoverMenuBar()
        menubar.set_menu_model(menubar_model)
        main_box.append(menubar)

        # ─── Workspace ───
        workspace = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        workspace.set_vexpand(True)
        main_box.append(workspace)

        # ─── Left panel: Toolbox + tool options ───
        left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left_panel.set_margin_start(4)
        left_panel.set_margin_top(4)
        left_panel.set_margin_bottom(4)
        left_panel.set_size_request(220, -1)

        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_vexpand(True)
        left_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left_scroll.set_child(left_inner)
        left_panel.append(left_scroll)

        # Tool buttons (vertical icon grid)
        self.tool_buttons = {}
        tools = [
            ("brush", _("Brush"), "edit-symbolic"),
            ("eraser", _("Eraser"), "edit-clear-symbolic"),
            ("line", _("Line"), "line-symbolic"),
            ("rectangle", _("Rectangle"), "view-grid-symbolic"),
            ("rounded_rectangle", _("Rounded Rect"), "view-grid-symbolic"),
            ("circle", _("Circle"), "media-record-symbolic"),
            ("polygon", _("Polygon"), "path-symbolic"),
            ("star", _("Star"), "starred-symbolic"),
            ("arrow", _("Arrow"), "go-next-symbolic"),
            ("fill", _("Fill"), "color-profile-symbolic"),
            ("text", _("Text"), "font-x-generic-symbolic"),
            ("select", _("Rect Select"), "selection-mode-symbolic"),
            ("select_ellipse", _("Ellipse Select"), "media-record-symbolic"),
            ("select_lasso", _("Lasso Select"), "path-symbolic"),
            ("select_color", _("Color Select"), "find-location-symbolic"),
            ("eyedropper", _("Eyedropper"), "color-select-symbolic"),
            ("spray", _("Spray"), "weather-fog-symbolic"),
            ("crop", _("Crop"), "edit-cut-symbolic"),
            ("gradient", _("Gradient"), "weather-clear-symbolic"),
            ("bezier", _("Bezier Path"), "path-symbolic"),
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

        left_inner.append(tool_flow)
        self.tool_buttons["brush"].set_active(True)

        left_inner.append(Gtk.Separator())

        # ─── Tool options ───
        opts_label = Gtk.Label(label=_("Tool Options"))
        opts_label.add_css_class("heading")
        opts_label.set_halign(Gtk.Align.START)
        left_inner.append(opts_label)

        # Brush size
        size_label = Gtk.Label(label=_("Size:"))
        size_label.set_halign(Gtk.Align.START)
        left_inner.append(size_label)
        self.size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.size_scale.set_value(5)
        self.size_scale.connect("value-changed", self.on_size_changed)
        left_inner.append(self.size_scale)

        # Opacity
        opacity_label = Gtk.Label(label=_("Opacity:"))
        opacity_label.set_halign(Gtk.Align.START)
        left_inner.append(opacity_label)
        self.opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.opacity_scale.set_value(100)
        self.opacity_scale.connect("value-changed", self.on_opacity_changed)
        left_inner.append(self.opacity_scale)

        # Stroke width
        stroke_label = Gtk.Label(label=_("Stroke Width:"))
        stroke_label.set_halign(Gtk.Align.START)
        left_inner.append(stroke_label)
        self.stroke_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 30, 1)
        self.stroke_scale.set_value(2)
        self.stroke_scale.connect("value-changed", self.on_stroke_width_changed)
        left_inner.append(self.stroke_scale)

        # Fill vs outline
        fill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.outline_btn = Gtk.ToggleButton(label=_("Outline"))
        self.outline_btn.set_active(True)
        self.outline_btn.connect("toggled", self.on_fill_mode_changed, "outline")
        fill_box.append(self.outline_btn)
        self.filled_btn = Gtk.ToggleButton(label=_("Filled"))
        self.filled_btn.connect("toggled", self.on_fill_mode_changed, "filled")
        fill_box.append(self.filled_btn)
        left_inner.append(fill_box)

        # Brush shape
        brush_shape_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.brush_shape_buttons = {}
        for shape_id, shape_name in [("round", _("Round")), ("square", _("Square")), ("calligraphy", _("Cal"))]:
            btn = Gtk.ToggleButton(label=shape_name)
            btn.connect("toggled", self.on_brush_shape_changed, shape_id)
            brush_shape_box.append(btn)
            self.brush_shape_buttons[shape_id] = btn
        self.brush_shape_buttons["round"].set_active(True)
        left_inner.append(brush_shape_box)

        # Smooth brush toggle
        self.smooth_check = Gtk.CheckButton(label=_("Smooth Brush"))
        self.smooth_check.set_active(True)
        self.smooth_check.connect("toggled", lambda b: setattr(self.drawing_area, 'smooth_brush', b.get_active()))
        left_inner.append(self.smooth_check)

        # Gradient mode
        gradient_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.gradient_buttons = {}
        for gid, gname in [("linear", _("Linear")), ("radial", _("Radial"))]:
            btn = Gtk.ToggleButton(label=gname)
            btn.connect("toggled", self.on_gradient_mode_changed, gid)
            gradient_box.append(btn)
            self.gradient_buttons[gid] = btn
        self.gradient_buttons["linear"].set_active(True)
        left_inner.append(gradient_box)

        # Fill tolerance
        tol_label = Gtk.Label(label=_("Tolerance:"))
        tol_label.set_halign(Gtk.Align.START)
        left_inner.append(tol_label)
        self.tolerance_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 128, 1)
        self.tolerance_scale.set_value(10)
        self.tolerance_scale.connect("value-changed", self._on_tolerance_changed)
        left_inner.append(self.tolerance_scale)

        # FG/BG color indicator
        self.fg_bg_widget = FgBgColorWidget(self.drawing_area)
        left_inner.append(self.fg_bg_widget)

        workspace.append(left_panel)
        workspace.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # ─── Center: Rulers + Canvas ───
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_hexpand(True)
        center_box.set_vexpand(True)

        # Horizontal ruler row
        ruler_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ruler_corner = Gtk.DrawingArea()
        ruler_corner.set_size_request(20, 20)
        ruler_row.append(ruler_corner)
        self.h_ruler = RulerWidget("horizontal")
        self.h_ruler.set_hexpand(True)
        ruler_row.append(self.h_ruler)
        center_box.append(ruler_row)

        # Canvas row with vertical ruler
        canvas_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.v_ruler = RulerWidget("vertical")
        self.v_ruler.set_vexpand(True)
        canvas_row.append(self.v_ruler)

        self.canvas_scroll = Gtk.ScrolledWindow()
        self.canvas_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.canvas_scroll.set_child(self.drawing_area)
        self.canvas_scroll.set_vexpand(True)
        self.canvas_scroll.set_hexpand(True)
        canvas_row.append(self.canvas_scroll)
        center_box.append(canvas_row)

        workspace.append(center_box)
        workspace.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # ─── Right panel: Colors + Layers ───
        right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right_panel.set_margin_end(4)
        right_panel.set_margin_top(4)
        right_panel.set_margin_bottom(4)
        right_panel.set_size_request(250, -1)

        right_scroll = Gtk.ScrolledWindow()
        right_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        right_scroll.set_vexpand(True)
        right_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_scroll.set_child(right_inner)
        right_panel.append(right_scroll)

        # HSV Color picker
        color_label = Gtk.Label(label=_("Color"))
        color_label.add_css_class("heading")
        color_label.set_halign(Gtk.Align.START)
        right_inner.append(color_label)

        self.hsv_widget = HSVColorWidget()
        self.hsv_widget.on_color_changed = self._on_hsv_color_changed
        right_inner.append(self.hsv_widget)

        # Palette
        palette_grid = Gtk.FlowBox()
        palette_grid.set_max_children_per_line(8)
        palette_grid.set_min_children_per_line(8)
        palette_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        palette_grid.set_homogeneous(True)
        for color in DEFAULT_PALETTE:
            rgba = (color[0], color[1], color[2], 1.0)
            btn = ColorSwatchButton(rgba, self._on_palette_color_selected)
            palette_grid.insert(btn, -1)
        right_inner.append(palette_grid)

        # Recent colors
        recent_label = Gtk.Label(label=_("Recent Colors:"))
        recent_label.set_halign(Gtk.Align.START)
        right_inner.append(recent_label)
        self.recent_flow = Gtk.FlowBox()
        self.recent_flow.set_max_children_per_line(10)
        self.recent_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.recent_flow.set_homogeneous(True)
        right_inner.append(self.recent_flow)

        right_inner.append(Gtk.Separator())

        # Layers section
        layers_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        layers_label = Gtk.Label(label=_("Layers"))
        layers_label.add_css_class("heading")
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
        flatten_btn = Gtk.Button()
        flatten_btn.set_icon_name("view-list-symbolic")
        flatten_btn.set_tooltip_text(_("Flatten Image"))
        flatten_btn.connect("clicked", lambda b: self._flatten_image())
        layers_header.append(flatten_btn)
        right_inner.append(layers_header)

        # Layer opacity
        lo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lo_box.append(Gtk.Label(label=_("Opacity:")))
        self.layer_opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.layer_opacity_scale.set_value(100)
        self.layer_opacity_scale.set_hexpand(True)
        self.layer_opacity_scale.connect("value-changed", self._on_layer_opacity_changed)
        lo_box.append(self.layer_opacity_scale)
        right_inner.append(lo_box)

        # Blend mode
        bm_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bm_box.append(Gtk.Label(label=_("Blend:")))
        self.blend_mode_combo = Gtk.DropDown()
        blend_model = Gtk.StringList.new([BLEND_MODE_LABELS[m] for m in BLEND_MODES])
        self.blend_mode_combo.set_model(blend_model)
        self.blend_mode_combo.set_selected(0)
        self.blend_mode_combo.connect("notify::selected", self._on_blend_mode_changed)
        self.blend_mode_combo.set_hexpand(True)
        bm_box.append(self.blend_mode_combo)
        right_inner.append(bm_box)

        self.layer_list_box = Gtk.ListBox()
        self.layer_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.layer_list_box.connect("row-selected", self.on_layer_selected)
        right_inner.append(self.layer_list_box)
        self._rebuild_layer_list()

        right_inner.append(Gtk.Separator())

        # Navigator thumbnail
        nav_label = Gtk.Label(label=_("Navigator"))
        nav_label.add_css_class("heading")
        nav_label.set_halign(Gtk.Align.START)
        right_inner.append(nav_label)
        self.navigator = Gtk.DrawingArea()
        self.navigator.set_size_request(200, 120)
        self.navigator.set_draw_func(self._draw_navigator)
        right_inner.append(self.navigator)

        workspace.append(right_panel)

        # ─── Status bar ───
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.status_box.add_css_class("toolbar")
        self.status_box.set_margin_start(8)
        self.status_box.set_margin_end(8)
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

        self.status_color_label = Gtk.Label(label="")
        self.status_box.append(self.status_color_label)

        self.status_mem_label = Gtk.Label(label="")
        self.status_box.append(self.status_mem_label)

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

    def _draw_navigator(self, area, ctx, w, h, data=None):
        """Draw canvas thumbnail in navigator"""
        da = self.drawing_area
        if not da.surface:
            return
        scale = min(w / max(1, da.width), h / max(1, da.height))
        tw = int(da.width * scale)
        th = int(da.height * scale)
        ox = (w - tw) // 2
        oy = (h - th) // 2
        ctx.set_source_rgb(0.2, 0.2, 0.2)
        ctx.paint()
        ctx.save()
        ctx.translate(ox, oy)
        ctx.scale(scale, scale)
        for layer in da.layers:
            if layer["visible"]:
                ctx.set_source_surface(layer["surface"], 0, 0)
                ctx.paint_with_alpha(layer.get("opacity", 1.0))
        ctx.restore()
        # Viewport rect
        ctx.set_source_rgba(1, 1, 0, 0.6)
        ctx.set_line_width(1)
        ctx.rectangle(ox, oy, tw, th)
        ctx.stroke()

    def _on_hsv_color_changed(self, rgba):
        """Handle HSV color widget change"""
        self.drawing_area.fg_color = rgba
        self._add_recent_color(rgba)
        self.fg_bg_widget.queue_draw()

    def _on_tolerance_changed(self, scale):
        self.drawing_area.fill_tolerance = int(scale.get_value())
        self.drawing_area.color_select_tolerance = int(scale.get_value())

    def _on_layer_opacity_changed(self, scale):
        da = self.drawing_area
        if da.layers and 0 <= da.active_layer_index < len(da.layers):
            da.layers[da.active_layer_index]["opacity"] = scale.get_value() / 100.0
            da.queue_draw()

    def _on_blend_mode_changed(self, combo, param):
        da = self.drawing_area
        idx = combo.get_selected()
        if da.layers and 0 <= da.active_layer_index < len(da.layers) and idx < len(BLEND_MODES):
            da.layers[da.active_layer_index]["blend_mode"] = BLEND_MODES[idx]
            da.queue_draw()

    def _flatten_image(self):
        """Flatten all layers"""
        da = self.drawing_area
        flat = da.flatten_layers()
        da.save_state_for_undo()
        da.layers = [{"name": _("Background"), "surface": flat, "visible": True,
                       "opacity": 1.0, "blend_mode": "normal"}]
        da.active_layer_index = 0
        da._sync_active_layer()
        self._rebuild_layer_list()
        da.queue_draw()

    def update_status_bar(self):
        """Update all status bar elements"""
        if not hasattr(self, 'status_tool_label'):
            return
        da = self.drawing_area
        tool_names = {
            "brush": _("Brush"), "eraser": _("Eraser"), "line": _("Line"),
            "rectangle": _("Rectangle"), "circle": _("Circle"),
            "polygon": _("Polygon"), "star": _("Star"), "fill": _("Fill"),
            "text": _("Text"), "select": _("Rect Select"),
            "select_ellipse": _("Ellipse Select"),
            "select_lasso": _("Lasso Select"),
            "select_color": _("Color Select"),
            "eyedropper": _("Eyedropper"), "spray": _("Spray"),
            "arrow": _("Arrow"), "rounded_rectangle": _("Rounded Rectangle"),
            "crop": _("Crop"), "gradient": _("Gradient"),
            "bezier": _("Bezier Path"),
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

        # Color under cursor
        r, g, b, a = da.fg_color
        self.status_color_label.set_text(
            "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255)))

        # Memory usage
        mem = sum(l["surface"].get_stride() * l["surface"].get_height() for l in da.layers)
        mem_mb = mem / (1024 * 1024)
        self.status_mem_label.set_text("{:.1f} MB".format(mem_mb))

        if self.current_file:
            self.status_file_label.set_text(os.path.basename(self.current_file))
        else:
            self.status_file_label.set_text("")

        # Update FG/BG indicator
        self.fg_bg_widget.queue_draw()

        # Update rulers
        if hasattr(self, 'h_ruler'):
            self.h_ruler.update_zoom(da.zoom_level)
            self.v_ruler.update_zoom(da.zoom_level)

        # Update navigator
        if hasattr(self, 'navigator'):
            self.navigator.queue_draw()

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
            # New actions
            ("scale_canvas", self.on_scale_canvas),
            ("shear_canvas", self.on_shear_canvas),
            ("perspective_canvas", self.on_perspective_canvas),
            ("add_layer", lambda a, p: (self.drawing_area.add_layer(), self._rebuild_layer_list())),
            ("delete_layer", lambda a, p: (self.drawing_area.delete_layer(), self._rebuild_layer_list())),
            ("flatten_image", lambda a, p: self._flatten_image()),
            ("brightness_contrast", self.on_brightness_contrast),
            ("hue_saturation", self.on_hue_saturation),
            ("color_curves", self.on_color_curves),
            ("grayscale", lambda a, p: self.drawing_area.convert_grayscale()),
            ("invert_colors", lambda a, p: self.drawing_area.invert_colors()),
            ("auto_levels", lambda a, p: self.drawing_area.auto_levels()),
            ("filter_blur", self.on_filter_blur),
            ("filter_sharpen", self.on_filter_sharpen),
            ("filter_emboss", lambda a, p: self.drawing_area.apply_emboss()),
            ("filter_edge_detect", lambda a, p: self.drawing_area.apply_edge_detect()),
            ("filter_pixelate", self.on_filter_pixelate),
            ("filter_noise", self.on_filter_noise),
            ("select_none", lambda a, p: self.drawing_area.select_none()),
            ("invert_selection", lambda a, p: self.drawing_area.invert_selection()),
            ("fit_to_window", self.on_fit_to_window),
            ("toggle_rulers", self.on_toggle_rulers),
            ("toggle_fullscreen", self.on_toggle_fullscreen),
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
            # Update opacity/blend controls
            layer = self.drawing_area.layers[idx]
            if hasattr(self, 'layer_opacity_scale'):
                self.layer_opacity_scale.set_value(layer.get("opacity", 1.0) * 100)
            if hasattr(self, 'blend_mode_combo'):
                bm = layer.get("blend_mode", "normal")
                bm_idx = BLEND_MODES.index(bm) if bm in BLEND_MODES else 0
                self.blend_mode_combo.set_selected(bm_idx)

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

    def on_toggle_rulers(self, action, param):
        da = self.drawing_area
        da.show_rulers = not da.show_rulers
        if hasattr(self, 'h_ruler'):
            self.h_ruler.set_visible(da.show_rulers)
            self.v_ruler.set_visible(da.show_rulers)

    def on_toggle_fullscreen(self, action, param):
        if self._is_fullscreen:
            self.unfullscreen()
        else:
            self.fullscreen()
        self._is_fullscreen = not self._is_fullscreen

    def on_fit_to_window(self, action, param):
        da = self.drawing_area
        alloc = self.canvas_scroll.get_allocation()
        if alloc.width > 0 and alloc.height > 0:
            zoom_w = alloc.width / max(1, da.width)
            zoom_h = alloc.height / max(1, da.height)
            da.zoom_level = min(zoom_w, zoom_h, 1.0)
            da.queue_draw()

    # ─── Transform actions ───

    def on_scale_canvas(self, action, param):
        dialog = ScaleDialog(self, self.drawing_area.width, self.drawing_area.height)
        dialog.connect("response", self._on_scale_response)
        dialog.present()

    def _on_scale_response(self, dialog, response):
        if response == "ok":
            w, h = dialog.get_dimensions()
            self.drawing_area.scale_canvas(w, h)
            self.update_status_bar()
        dialog.destroy()

    def on_shear_canvas(self, action, param):
        dialog = ShearDialog(self)
        dialog.connect("response", self._on_shear_response)
        dialog.present()

    def _on_shear_response(self, dialog, response):
        if response == "ok":
            sx = dialog.shear_x.get_value()
            sy = dialog.shear_y.get_value()
            if sx != 0 or sy != 0:
                self.drawing_area.shear_canvas(sx, sy)
                self.update_status_bar()
        dialog.destroy()

    def on_perspective_canvas(self, action, param):
        dialog = PerspectiveDialog(self)
        dialog.connect("response", self._on_perspective_response)
        dialog.present()

    def _on_perspective_response(self, dialog, response):
        if response == "ok":
            top = dialog.top_scale.get_value()
            bottom = dialog.bottom_scale.get_value()
            if top != 0 or bottom != 0:
                self.drawing_area.perspective_transform(top, bottom)
        dialog.destroy()

    # ─── Image adjustment actions ───

    def on_brightness_contrast(self, action, param):
        dialog = AdjustmentDialog(self, _("Brightness/Contrast"), [
            ("brightness", _("Brightness:"), -100, 100, 0),
            ("contrast", _("Contrast:"), -100, 100, 0),
        ])
        dialog.connect("response", self._on_bc_response)
        dialog.present()

    def _on_bc_response(self, dialog, response):
        if response == "ok":
            b = int(dialog.get_value("brightness"))
            c = int(dialog.get_value("contrast"))
            self.drawing_area.adjust_brightness_contrast(b, c)
        dialog.destroy()

    def on_hue_saturation(self, action, param):
        dialog = AdjustmentDialog(self, _("Hue/Saturation"), [
            ("hue", _("Hue Shift:"), -180, 180, 0),
            ("saturation", _("Saturation:"), -100, 100, 0),
        ])
        dialog.connect("response", self._on_hs_response)
        dialog.present()

    def _on_hs_response(self, dialog, response):
        if response == "ok":
            h = int(dialog.get_value("hue"))
            s = int(dialog.get_value("saturation"))
            self.drawing_area.adjust_hue_saturation(h, s)
        dialog.destroy()

    def on_color_curves(self, action, param):
        dialog = ColorCurvesDialog(self)
        dialog.connect("response", self._on_curves_response)
        dialog.present()

    def _on_curves_response(self, dialog, response):
        if response == "ok":
            lut = dialog.generate_lut()
            self.drawing_area.apply_curves(lut)
        dialog.destroy()

    # ─── Filter actions ───

    def on_filter_blur(self, action, param):
        dialog = AdjustmentDialog(self, _("Blur"), [
            ("radius", _("Radius:"), 1, 20, 3),
        ])
        dialog.connect("response", self._on_blur_response)
        dialog.present()

    def _on_blur_response(self, dialog, response):
        if response == "ok":
            r = int(dialog.get_value("radius"))
            self.drawing_area.apply_blur(r)
        dialog.destroy()

    def on_filter_sharpen(self, action, param):
        dialog = AdjustmentDialog(self, _("Sharpen"), [
            ("amount", _("Amount:"), 1, 10, 1),
        ])
        dialog.connect("response", self._on_sharpen_response)
        dialog.present()

    def _on_sharpen_response(self, dialog, response):
        if response == "ok":
            a = dialog.get_value("amount")
            self.drawing_area.apply_sharpen(a)
        dialog.destroy()

    def on_filter_pixelate(self, action, param):
        dialog = AdjustmentDialog(self, _("Pixelate"), [
            ("size", _("Block Size:"), 2, 64, 8),
        ])
        dialog.connect("response", self._on_pixelate_response)
        dialog.present()

    def _on_pixelate_response(self, dialog, response):
        if response == "ok":
            s = int(dialog.get_value("size"))
            self.drawing_area.apply_pixelate(s)
        dialog.destroy()

    def on_filter_noise(self, action, param):
        dialog = AdjustmentDialog(self, _("Noise"), [
            ("amount", _("Amount:"), 1, 100, 30),
        ])
        dialog.connect("response", self._on_noise_response)
        dialog.present()

    def _on_noise_response(self, dialog, response):
        if response == "ok":
            a = int(dialog.get_value("amount"))
            self.drawing_area.apply_noise(a)
        dialog.destroy()

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
            da.layers.insert(insert_idx, {"name": layer_name, "surface": new_surface, "visible": True,
                                          "opacity": 1.0, "blend_mode": "normal"})
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

        # New selection tools
        self.set_accels_for_action("win.tool_select_ellipse", ["<Shift>e"])
        self.set_accels_for_action("win.tool_select_lasso", ["<Shift>l"])
        self.set_accels_for_action("win.tool_select_color", ["<Shift>u"])
        self.set_accels_for_action("win.tool_bezier", ["n"])

        # Selection actions
        self.set_accels_for_action("win.select_none", ["<Control><Shift>a"])
        self.set_accels_for_action("win.invert_selection", ["<Control>i"])

        # View
        self.set_accels_for_action("win.toggle_fullscreen", ["F11"])
        self.set_accels_for_action("win.fit_to_window", ["<Control><Shift>e"])

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
        about.set_version("2.0.0")
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
