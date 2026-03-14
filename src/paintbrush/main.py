#!/usr/bin/env python3
"""
PaintBrush - Enhanced version with additional features
Modern GTK4 application with Cairo graphics
Version 1.3.0 with new tools and functionality
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gdk, GdkPixbuf, Gio, GLib, GObject
import cairo
import math
import os
import locale
import gettext
import json
import ctypes
from pathlib import Path

# Internationalization setup
GETTEXT_DOMAIN = 'paintbrush'
LOCALE_DIR = '/usr/share/locale'

# Try to set up locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

# Set up gettext
gettext.bindtextdomain(GETTEXT_DOMAIN, LOCALE_DIR)
gettext.textdomain(GETTEXT_DOMAIN)
_ = gettext.gettext

# Config directory for settings
CONFIG_DIR = Path(GLib.get_user_config_dir()) / "paintbrush"


def _load_settings():
    path = CONFIG_DIR / "settings.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


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
        """Save current canvas state"""
        # Remove any future states if we're not at the end
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]

        # Create a copy of the surface
        surface_copy = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                        surface.get_width(),
                                        surface.get_height())
        ctx = cairo.Context(surface_copy)
        ctx.set_source_surface(surface, 0, 0)
        ctx.paint()

        self.history.append(surface_copy)
        self.current_index += 1

        # Limit history size
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
    """Enhanced drawing area with new tools and features"""

    def __init__(self):
        super().__init__()

        # Canvas properties
        self.width = 800
        self.height = 600
        self.surface = None
        self.ctx = None
        self.zoom_level = 1.0

        # Drawing state
        self.drawing = False
        self.last_x = 0
        self.last_y = 0

        # Tool properties
        self.tool = "brush"  # brush, eraser, line, rectangle, circle, polygon, star, fill, text
        self.brush_size = 5
        self.color = (0, 0, 0)  # RGB
        self.line_width = 2

        # New tool properties
        self.fill_tolerance = 10
        self.polygon_points = []
        self.text_content = ""
        self.font_size = 16

        # Undo/Redo
        self.undo_manager = UndoRedoManager()

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

        self.add_controller(self.gesture_click)
        self.add_controller(self.gesture_drag)

        # Initialize canvas
        self.initialize_surface()

    def initialize_surface(self):
        """Initialize the drawing surface"""
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        self.ctx = cairo.Context(self.surface)

        # Fill with white background
        self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.paint()

        # Save initial state
        self.undo_manager.save_state(self.surface)

    def on_draw(self, area, ctx, width, height, user_data=None):
        """Draw callback - render the surface to screen with zoom"""
        if self.surface:
            ctx.scale(self.zoom_level, self.zoom_level)
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.paint()

    def save_state_for_undo(self):
        """Save current state before making changes"""
        self.undo_manager.save_state(self.surface)

    def undo(self):
        """Undo last operation"""
        previous_surface = self.undo_manager.undo()
        if previous_surface:
            # Copy the previous surface to current
            self.ctx.set_operator(cairo.OPERATOR_SOURCE)
            self.ctx.set_source_surface(previous_surface, 0, 0)
            self.ctx.paint()
            self.ctx.set_operator(cairo.OPERATOR_OVER)
            self.queue_draw()
            return True
        return False

    def redo(self):
        """Redo last undone operation"""
        next_surface = self.undo_manager.redo()
        if next_surface:
            # Copy the next surface to current
            self.ctx.set_operator(cairo.OPERATOR_SOURCE)
            self.ctx.set_source_surface(next_surface, 0, 0)
            self.ctx.paint()
            self.ctx.set_operator(cairo.OPERATOR_OVER)
            self.queue_draw()
            return True
        return False

    def zoom_in(self):
        """Zoom in by 25%"""
        self.zoom_level = min(4.0, self.zoom_level * 1.25)
        self.queue_draw()

    def zoom_out(self):
        """Zoom out by 25%"""
        self.zoom_level = max(0.25, self.zoom_level / 1.25)
        self.queue_draw()

    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.zoom_level = 1.0
        self.queue_draw()

    def on_drag_begin(self, gesture, start_x, start_y):
        """Start drawing operation"""
        # Adjust coordinates for zoom
        start_x /= self.zoom_level
        start_y /= self.zoom_level

        self.drawing = True
        self.last_x = start_x
        self.last_y = start_y

        if self.tool in ["brush", "eraser"]:
            self.save_state_for_undo()

        if self.tool == "brush":
            self.draw_dot(start_x, start_y)
        elif self.tool == "eraser":
            self.erase_dot(start_x, start_y)
        elif self.tool == "fill":
            self.save_state_for_undo()
            self.flood_fill(int(start_x), int(start_y))
        elif self.tool == "polygon":
            self.polygon_points.append((start_x, start_y))
        elif self.tool == "text":
            self.save_state_for_undo()
            self.draw_text(start_x, start_y)

    def on_button_press(self, gesture, n_press, x, y):
        """Handle button press for single-click tools"""
        # Adjust coordinates for zoom
        x /= self.zoom_level
        y /= self.zoom_level

        if self.tool in ["brush", "eraser", "fill", "text"]:
            return

        if self.tool == "polygon" and n_press == 2:  # Double-click to finish polygon
            if len(self.polygon_points) > 2:
                self.save_state_for_undo()
                self.draw_polygon()
                self.polygon_points = []
            return

        self.last_x = x
        self.last_y = y
        self.drawing = True

    def on_button_release(self, gesture, n_press, x, y):
        """Handle button release - finalize shapes"""
        if not self.drawing:
            return

        # Adjust coordinates for zoom
        x /= self.zoom_level
        y /= self.zoom_level

        self.drawing = False

        if self.tool in ["line", "rectangle", "circle", "star"]:
            self.save_state_for_undo()

        if self.tool == "line":
            self.draw_line(self.last_x, self.last_y, x, y)
        elif self.tool == "rectangle":
            self.draw_rectangle(self.last_x, self.last_y, x, y)
        elif self.tool == "circle":
            self.draw_circle(self.last_x, self.last_y, x, y)
        elif self.tool == "star":
            self.draw_star(self.last_x, self.last_y, x, y)

        self.queue_draw()

    def on_motion_notify(self, gesture, offset_x, offset_y):
        """Handle mouse/touch drag"""
        if not self.drawing:
            return

        # Adjust coordinates for zoom
        current_x = self.last_x + (offset_x / self.zoom_level)
        current_y = self.last_y + (offset_y / self.zoom_level)

        if self.tool == "brush":
            self.draw_line_segment(self.last_x, self.last_y, current_x, current_y)
            self.last_x = current_x
            self.last_y = current_y
        elif self.tool == "eraser":
            self.erase_line_segment(self.last_x, self.last_y, current_x, current_y)
            self.last_x = current_x
            self.last_y = current_y

        self.queue_draw()

    def draw_star(self, x1, y1, x2, y2):
        """Draw a star shape"""
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2

        self.ctx.set_source_rgb(*self.color)
        self.ctx.set_line_width(self.line_width)

        # Draw 5-pointed star
        points = 10
        angle_step = 2 * math.pi / points

        for i in range(points):
            angle = i * angle_step - math.pi/2
            if i % 2 == 0:
                # Outer point
                r = radius
            else:
                # Inner point
                r = radius * 0.4

            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)

            if i == 0:
                self.ctx.move_to(x, y)
            else:
                self.ctx.line_to(x, y)

        self.ctx.close_path()
        self.ctx.stroke()

    def draw_polygon(self):
        """Draw polygon from collected points"""
        if len(self.polygon_points) < 3:
            return

        self.ctx.set_source_rgb(*self.color)
        self.ctx.set_line_width(self.line_width)

        # Move to first point
        self.ctx.move_to(*self.polygon_points[0])

        # Draw lines to other points
        for point in self.polygon_points[1:]:
            self.ctx.line_to(*point)

        # Close the polygon
        self.ctx.close_path()
        self.ctx.stroke()

    def flood_fill(self, x, y):
        """Simple flood fill implementation"""
        self.ctx.set_source_rgb(*self.color)
        self.ctx.arc(x, y, 20, 0, 2 * math.pi)
        self.ctx.fill()

    def draw_text(self, x, y):
        """Draw text at specified position"""
        if not self.text_content:
            self.text_content = _("Text")

        self.ctx.set_source_rgb(*self.color)
        self.ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.ctx.set_font_size(self.font_size)
        self.ctx.move_to(x, y)
        self.ctx.show_text(self.text_content)

    def draw_dot(self, x, y):
        """Draw a single dot"""
        self.ctx.set_source_rgb(*self.color)
        self.ctx.arc(x, y, self.brush_size/2, 0, 2 * math.pi)
        self.ctx.fill()
        self.queue_draw()

    def erase_dot(self, x, y):
        """Erase a single dot"""
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.arc(x, y, self.brush_size, 0, 2 * math.pi)
        self.ctx.fill()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
        self.queue_draw()

    def draw_line_segment(self, x1, y1, x2, y2):
        """Draw line segment for brush strokes"""
        self.ctx.set_source_rgb(*self.color)
        self.ctx.set_line_width(self.brush_size)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.stroke()

    def erase_line_segment(self, x1, y1, x2, y2):
        """Erase line segment"""
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.set_line_width(self.brush_size * 2)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.stroke()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def draw_line(self, x1, y1, x2, y2):
        """Draw straight line"""
        self.ctx.set_source_rgb(*self.color)
        self.ctx.set_line_width(self.line_width)
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.stroke()

    def draw_rectangle(self, x1, y1, x2, y2):
        """Draw rectangle"""
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        self.ctx.set_source_rgb(*self.color)
        self.ctx.set_line_width(self.line_width)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.stroke()

    def draw_circle(self, x1, y1, x2, y2):
        """Draw circle/ellipse"""
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2

        self.ctx.set_source_rgb(*self.color)
        self.ctx.set_line_width(self.line_width)
        self.ctx.arc(center_x, center_y, radius, 0, 2 * math.pi)
        self.ctx.stroke()

    def clear_canvas(self):
        """Clear the entire canvas"""
        self.save_state_for_undo()
        self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.paint()
        self.queue_draw()

    def save_image(self, filename):
        """Save canvas to file"""
        self.surface.write_to_png(filename)

    def load_image(self, filename):
        """Load image into canvas using GdkPixbuf with manual pixel painting"""
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)

            # Save state before loading
            self.save_state_for_undo()

            pw = pixbuf.get_width()
            ph = pixbuf.get_height()
            has_alpha = pixbuf.get_has_alpha()
            n_channels = pixbuf.get_n_channels()
            rowstride = pixbuf.get_rowstride()

            # Create a Cairo surface matching pixbuf dimensions
            img_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw, ph)

            # Get raw pixel data from both
            pixels = pixbuf.get_pixels()
            buf = img_surface.get_data()

            for y in range(ph):
                for x in range(pw):
                    src_offset = y * rowstride + x * n_channels
                    r = pixels[src_offset]
                    g = pixels[src_offset + 1]
                    b = pixels[src_offset + 2]
                    a = pixels[src_offset + 3] if has_alpha else 255

                    # Cairo ARGB32 is stored as pre-multiplied BGRA in native byte order
                    dst_offset = y * img_surface.get_stride() + x * 4
                    # Pre-multiply alpha
                    buf[dst_offset] = b * a // 255      # B
                    buf[dst_offset + 1] = g * a // 255  # G
                    buf[dst_offset + 2] = r * a // 255  # R
                    buf[dst_offset + 3] = a             # A

            img_surface.mark_dirty()

            # Draw onto our canvas
            self.ctx.set_source_surface(img_surface, 0, 0)
            self.ctx.paint()
            self.queue_draw()
        except Exception as e:
            print(f"Error loading image: {e}")

class ColorButton(Gtk.Button):
    """Custom color button for palette"""

    def __init__(self, color, drawing_area):
        super().__init__()
        self.color = color
        self.drawing_area = drawing_area

        # Create a small drawing area to show the color
        color_swatch = Gtk.DrawingArea()
        color_swatch.set_size_request(24, 24)
        color_swatch.set_draw_func(self._draw_swatch)
        self.set_child(color_swatch)

        self.connect("clicked", self.on_clicked)

    def _draw_swatch(self, area, ctx, width, height, user_data=None):
        ctx.set_source_rgb(*self.color)
        ctx.paint()

    def on_clicked(self, button):
        """Set drawing color"""
        self.drawing_area.color = self.color

class TextInputDialog(Adw.MessageDialog):
    """Dialog for text input"""

    def __init__(self, parent, current_text=""):
        super().__init__(transient_for=parent)
        self.set_heading(_("Enter Text"))
        self.add_response("cancel", _("Cancel"))
        self.add_response("ok", _("OK"))
        self.set_default_response("ok")
        self.set_close_response("cancel")

        # Text entry
        self.text_entry = Gtk.Entry()
        self.text_entry.set_text(current_text)
        self.text_entry.set_placeholder_text(_("Enter text to draw"))

        # Font size entry
        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        font_label = Gtk.Label(label=_("Font Size:"))
        self.font_entry = Gtk.SpinButton.new_with_range(8, 72, 1)
        self.font_entry.set_value(16)

        font_box.append(font_label)
        font_box.append(self.font_entry)

        # Main container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.append(self.text_entry)
        content_box.append(font_box)

        self.set_extra_child(content_box)

    def get_text(self):
        return self.text_entry.get_text()

    def get_font_size(self):
        return int(self.font_entry.get_value())

class PaintBrushWindow(Adw.ApplicationWindow):
    """Enhanced main window with new tools"""

    def __init__(self, app):
        super().__init__(application=app)

        self.set_title(_("PaintBrush"))
        self.set_default_size(1000, 700)

        # Current save path
        self.current_file = None

        # Create drawing area
        self.drawing_area = DrawingArea()

        # Setup UI
        self.setup_ui()

        # Setup actions
        self.setup_actions()

        # Setup keyboard shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Undo/Redo
        undo_action = Gio.SimpleAction.new("undo", None)
        undo_action.connect("activate", self.on_undo)
        self.add_action(undo_action)

        redo_action = Gio.SimpleAction.new("redo", None)
        redo_action.connect("activate", self.on_redo)
        self.add_action(redo_action)

        # Zoom
        zoom_in_action = Gio.SimpleAction.new("zoom_in", None)
        zoom_in_action.connect("activate", self.on_zoom_in)
        self.add_action(zoom_in_action)

        zoom_out_action = Gio.SimpleAction.new("zoom_out", None)
        zoom_out_action.connect("activate", self.on_zoom_out)
        self.add_action(zoom_out_action)

        zoom_reset_action = Gio.SimpleAction.new("zoom_reset", None)
        zoom_reset_action.connect("activate", self.on_zoom_reset)
        self.add_action(zoom_reset_action)

        # Shortcuts window
        shortcuts_action = Gio.SimpleAction.new("show-shortcuts", None)
        shortcuts_action.connect("activate", self.on_show_shortcuts)
        self.add_action(shortcuts_action)

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
        }
        for action_name, tool_id in tool_keys.items():
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", self._on_tool_shortcut, tool_id)
            self.add_action(action)

    def _on_tool_shortcut(self, action, param, tool_id):
        """Activate tool via keyboard shortcut"""
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
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">New</property>
                        <property name="accelerator">&lt;Primary&gt;n</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Open</property>
                        <property name="accelerator">&lt;Primary&gt;o</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Save</property>
                        <property name="accelerator">&lt;Primary&gt;s</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Save As</property>
                        <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;s</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Quit</property>
                        <property name="accelerator">&lt;Primary&gt;q</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">Edit</property>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Undo</property>
                        <property name="accelerator">&lt;Primary&gt;z</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Redo</property>
                        <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;z</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">View</property>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Zoom In</property>
                        <property name="accelerator">&lt;Primary&gt;plus</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Zoom Out</property>
                        <property name="accelerator">&lt;Primary&gt;minus</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Reset Zoom</property>
                        <property name="accelerator">&lt;Primary&gt;0</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkShortcutsGroup">
                    <property name="title" translatable="yes">Tools</property>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Brush</property>
                        <property name="accelerator">b</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Eraser</property>
                        <property name="accelerator">e</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Line</property>
                        <property name="accelerator">l</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Rectangle</property>
                        <property name="accelerator">r</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Circle</property>
                        <property name="accelerator">c</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Text</property>
                        <property name="accelerator">t</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Fill</property>
                        <property name="accelerator">f</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Star</property>
                        <property name="accelerator">s</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkShortcutsShortcut">
                        <property name="title" translatable="yes">Polygon</property>
                        <property name="accelerator">p</property>
                      </object>
                    </child>
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
        """Create the user interface with new tools"""
        # Main box
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
        menu.append_section(None, file_section)

        edit_section = Gio.Menu()
        edit_section.append(_("Undo"), "win.undo")
        edit_section.append(_("Redo"), "win.redo")
        menu.append_section(None, edit_section)

        zoom_section = Gio.Menu()
        zoom_section.append(_("Zoom In"), "win.zoom_in")
        zoom_section.append(_("Zoom Out"), "win.zoom_out")
        zoom_section.append(_("Zoom Reset"), "win.zoom_reset")
        menu.append_section(None, zoom_section)

        canvas_section = Gio.Menu()
        canvas_section.append(_("Clear Canvas"), "win.clear")
        menu.append_section(None, canvas_section)

        app_section = Gio.Menu()
        app_section.append(_("Keyboard Shortcuts"), "win.show-shortcuts")
        app_section.append(_("About PaintBrush"), "app.about")
        app_section.append(_("Quit"), "app.quit")
        menu.append_section(None, app_section)

        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        main_box.append(toolbar)

        # Tool buttons - enhanced with new tools
        tools_label = Gtk.Label(label=_("Tools:"))
        tools_label.add_css_class("heading")
        toolbar.append(tools_label)

        # Tool button group
        self.tool_buttons = {}
        tools = [
            ("brush", _("Brush"), "edit-symbolic"),
            ("eraser", _("Eraser"), "edit-clear-symbolic"),
            ("line", _("Line"), "line-symbolic"),
            ("rectangle", _("Rectangle"), "view-grid-symbolic"),
            ("circle", _("Circle"), "media-record-symbolic"),
            ("polygon", _("Polygon"), "path-symbolic"),
            ("star", _("Star"), "starred-symbolic"),
            ("fill", _("Fill"), "paint-bucket-symbolic"),
            ("text", _("Text"), "text-symbolic")
        ]

        for tool_id, label, icon in tools:
            btn = Gtk.ToggleButton()
            btn.set_icon_name(icon)
            btn.set_tooltip_text(label)
            btn.connect("toggled", self.on_tool_changed, tool_id)
            toolbar.append(btn)
            self.tool_buttons[tool_id] = btn

        # Set brush as default
        self.tool_buttons["brush"].set_active(True)

        toolbar.append(Gtk.Separator())

        # Brush size
        size_label = Gtk.Label(label=_("Size:"))
        toolbar.append(size_label)

        self.size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 50, 1)
        self.size_scale.set_value(5)
        self.size_scale.set_size_request(100, -1)
        self.size_scale.connect("value-changed", self.on_size_changed)
        toolbar.append(self.size_scale)

        toolbar.append(Gtk.Separator())

        # Color palette - enhanced
        colors_label = Gtk.Label(label=_("Colors:"))
        toolbar.append(colors_label)

        # Basic color palette
        colors = [
            (0, 0, 0),        # Black
            (1, 0, 0),        # Red
            (0, 1, 0),        # Green
            (0, 0, 1),        # Blue
            (1, 1, 0),        # Yellow
            (1, 0, 1),        # Magenta
            (0, 1, 1),        # Cyan
            (1, 1, 1),        # White
            (0.5, 0.5, 0.5),  # Gray
            (1, 0.5, 0),      # Orange
            (0.5, 0, 0.5),    # Purple
            (0.5, 0.5, 0),    # Olive
        ]

        for color in colors:
            color_btn = ColorButton(color, self.drawing_area)
            color_btn.set_size_request(32, 32)
            toolbar.append(color_btn)

        # Scrolled window for drawing area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.drawing_area)
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        # Status bar
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.add_css_class("toolbar")
        status_box.set_margin_start(12)
        status_box.set_margin_end(12)

        self.status_label = Gtk.Label(label=_("Ready"))
        self.status_label.set_halign(Gtk.Align.START)
        status_box.append(self.status_label)

        # Zoom indicator
        self.zoom_label = Gtk.Label(label="100%")
        self.zoom_label.set_halign(Gtk.Align.END)
        status_box.append(self.zoom_label)

        main_box.append(status_box)

        # Update zoom label periodically
        GLib.timeout_add(500, self.update_zoom_label)

    def update_zoom_label(self):
        """Update zoom level display"""
        zoom_percent = int(self.drawing_area.zoom_level * 100)
        self.zoom_label.set_text(f"{zoom_percent}%")
        return True  # Continue timeout

    def setup_actions(self):
        """Setup application actions"""
        # File actions
        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        open_action = Gio.SimpleAction.new("open", None)
        open_action.connect("activate", self.on_open)
        self.add_action(open_action)

        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.on_save)
        self.add_action(save_action)

        save_as_action = Gio.SimpleAction.new("save_as", None)
        save_as_action.connect("activate", self.on_save_as)
        self.add_action(save_as_action)

        clear_action = Gio.SimpleAction.new("clear", None)
        clear_action.connect("activate", self.on_clear)
        self.add_action(clear_action)

    def on_tool_changed(self, button, tool_id):
        """Handle tool selection"""
        if button.get_active():
            # Deactivate other tool buttons
            for tid, btn in self.tool_buttons.items():
                if tid != tool_id:
                    btn.set_active(False)

            self.drawing_area.tool = tool_id

            # Special handling for text tool
            if tool_id == "text":
                self.show_text_dialog()

            hasattr(self, "status_label") and self.status_label.set_text(_("Tool: {}").format(_(tool_id.title())))

    def show_text_dialog(self):
        """Show text input dialog"""
        dialog = TextInputDialog(self, self.drawing_area.text_content)
        dialog.connect("response", self.on_text_dialog_response)
        dialog.present()

    def on_text_dialog_response(self, dialog, response):
        """Handle text dialog response"""
        if response == "ok":
            self.drawing_area.text_content = dialog.get_text()
            self.drawing_area.font_size = dialog.get_font_size()
        dialog.destroy()

    def on_size_changed(self, scale):
        """Handle brush size change"""
        size = int(scale.get_value())
        self.drawing_area.brush_size = size
        self.drawing_area.line_width = max(1, size // 2)

    # Undo/Redo actions
    def on_undo(self, action, param):
        """Undo last operation"""
        if self.drawing_area.undo():
            hasattr(self, "status_label") and self.status_label.set_text(_("Undone"))
        else:
            hasattr(self, "status_label") and self.status_label.set_text(_("Nothing to undo"))

    def on_redo(self, action, param):
        """Redo last undone operation"""
        if self.drawing_area.redo():
            hasattr(self, "status_label") and self.status_label.set_text(_("Redone"))
        else:
            hasattr(self, "status_label") and self.status_label.set_text(_("Nothing to redo"))

    # Zoom actions
    def on_zoom_in(self, action, param):
        """Zoom in"""
        self.drawing_area.zoom_in()
        hasattr(self, "status_label") and self.status_label.set_text(_("Zoomed in"))

    def on_zoom_out(self, action, param):
        """Zoom out"""
        self.drawing_area.zoom_out()
        hasattr(self, "status_label") and self.status_label.set_text(_("Zoomed out"))

    def on_zoom_reset(self, action, param):
        """Reset zoom"""
        self.drawing_area.zoom_reset()
        hasattr(self, "status_label") and self.status_label.set_text(_("Zoom reset"))

    # File actions using modern Gtk.FileDialog
    def on_new(self, action, param):
        """Create new canvas"""
        self.drawing_area.clear_canvas()
        self.current_file = None
        hasattr(self, "status_label") and self.status_label.set_text(_("New canvas created"))

    def on_open(self, action, param):
        """Open image file using Gtk.FileDialog"""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Open Image"))

        filter_images = Gtk.FileFilter()
        filter_images.set_name(_("Images"))
        filter_images.add_mime_type("image/png")
        filter_images.add_mime_type("image/jpeg")
        filter_images.add_mime_type("image/gif")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_images)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_images)

        dialog.open(self, None, self._on_open_finish)

    def _on_open_finish(self, dialog, result):
        """Handle open file dialog result"""
        try:
            file = dialog.open_finish(result)
            if file:
                filename = file.get_path()
                self.drawing_area.load_image(filename)
                self.current_file = filename
                hasattr(self, "status_label") and self.status_label.set_text(_("Opened: {}").format(os.path.basename(filename)))
        except GLib.Error:
            pass  # User cancelled

    def on_save(self, action, param):
        """Quick save - save to current file or prompt"""
        if self.current_file:
            self.drawing_area.save_image(self.current_file)
            hasattr(self, "status_label") and self.status_label.set_text(_("Saved: {}").format(os.path.basename(self.current_file)))
        else:
            self.on_save_as(action, param)

    def on_save_as(self, action, param):
        """Save as dialog using Gtk.FileDialog"""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Save Image"))
        dialog.set_initial_name("artwork.png")

        filter_png = Gtk.FileFilter()
        filter_png.set_name(_("PNG Images"))
        filter_png.add_mime_type("image/png")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_png)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_png)

        dialog.save(self, None, self._on_save_finish)

    def _on_save_finish(self, dialog, result):
        """Handle save file dialog result"""
        try:
            file = dialog.save_finish(result)
            if file:
                filename = file.get_path()
                if not filename.endswith('.png'):
                    filename += '.png'
                self.drawing_area.save_image(filename)
                self.current_file = filename
                hasattr(self, "status_label") and self.status_label.set_text(_("Saved: {}").format(os.path.basename(filename)))
        except GLib.Error:
            pass  # User cancelled

    def on_clear(self, action, param):
        """Clear canvas"""
        self.drawing_area.clear_canvas()
        hasattr(self, "status_label") and self.status_label.set_text(_("Canvas cleared"))

class PaintBrushApp(Adw.Application):
    """Enhanced main application class"""

    def __init__(self):
        super().__init__(application_id="com.danielnylander.paintbrush")
        self.set_flags(Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.settings = _load_settings()

    def do_activate(self):
        """Application activation"""
        window = PaintBrushWindow(self)
        window.present()

        # Show welcome screen on first run
        if not self.settings.get("welcome_shown"):
            self._show_welcome(window)

    def _show_welcome(self, win):
        """Show welcome dialog on first launch"""
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(400)

        page = Adw.StatusPage()
        page.set_icon_name("com.danielnylander.paintbrush")
        page.set_title(_("Welcome to PaintBrush"))
        page.set_description(_("A simple painting app for Linux"))

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        page.set_child(btn)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.set_child(box)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        """Close welcome dialog and mark as shown"""
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()

    def do_startup(self):
        """Application startup - setup keyboard shortcuts"""
        Adw.Application.do_startup(self)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

        # Set up keyboard accelerators
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

    def _on_about(self, action, param):
        """Show About dialog"""
        about = Adw.AboutDialog()
        about.set_application_name(_("PaintBrush"))
        about.set_application_icon("com.danielnylander.paintbrush")
        about.set_developer_name("Daniel Nylander")
        about.set_version("1.3.0")
        about.set_website("https://github.com/yeager/paintbrush")
        about.set_issue_url("https://github.com/yeager/paintbrush/issues")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_copyright("© 2026 Daniel Nylander")
        about.add_link(_("Help translate"), "https://app.transifex.com/danielnylander/paintbrush")
        about.present(self.get_active_window())

    def _on_quit(self, action, param):
        """Quit the application"""
        self.quit()

def main():
    """Main entry point"""
    app = PaintBrushApp()
    return app.run([])

if __name__ == "__main__":
    main()
