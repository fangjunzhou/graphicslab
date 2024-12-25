import dataclasses
from typing import Callable
import copy

from imgui_bundle import imgui, imgui_ctx

from graphicslab.window import Window
from graphicslab.settings.decorator import SettingsField, FieldStyle
from graphicslab.settings.settings import Settings, SettingsState
from graphicslab.settings.utils import save_settings


def render_int_field(field: SettingsField[int]):
    if field.style == FieldStyle.INPUT:
        changed, field.value = imgui.input_int(
            field.disp_name,
            field.value,
        )
    elif field.style == FieldStyle.SLIDER:
        changed, field.value = imgui.slider_int(
            field.disp_name,
            field.value,
            field.v_min_i,
            field.v_max_i,
            flags=field.slider_flags
        )
    elif field.style == FieldStyle.DRAG:
        changed, field.value = imgui.drag_int(
            field.disp_name,
            field.value,
            field.speed,
            field.v_min_i,
            field.v_max_i,
            flags=field.slider_flags
        )
    else:
        # Unsupported style.
        changed = False
    return changed


def render_float_field(field: SettingsField[float]):
    if field.style == FieldStyle.INPUT:
        changed, field.value = imgui.input_float(
            field.disp_name,
            field.value,
            field.step
        )
    elif field.style == FieldStyle.SLIDER:
        changed, field.value = imgui.slider_float(
            field.disp_name,
            field.value,
            field.v_min_f,
            field.v_max_f,
            flags=field.slider_flags
        )
    elif field.style == FieldStyle.DRAG:
        changed, field.value = imgui.drag_float(
            field.disp_name,
            field.value,
            field.speed,
            field.v_min_f,
            field.v_max_f,
            flags=field.slider_flags
        )
    else:
        # Unsupported style.
        changed = False
    return changed


def render_bool_field(field: SettingsField[bool]):
    changed, field.value = imgui.checkbox(
        field.disp_name,
        field.value
    )
    return changed


def render_settings_field(field: SettingsField):
    changed = False
    # Render field.
    if type(field.value) is int:
        changed = render_int_field(field)
    elif type(field.value) is float:
        changed = render_float_field(field)
    elif type(field.value) is bool:
        changed = render_bool_field(field)
    elif type(field.value) is str:
        # TODO: str field rendering.
        pass
    else:
        # Unsupported field type.
        pass
    # Render help message.
    if field.tooltip != "":
        imgui.set_item_tooltip(field.tooltip)
    return changed


class SettingsWindow(Window):
    settings_state: SettingsState
    unsaved_settings: Settings
    unsave: bool = False

    def __init__(self, close_window: Callable[[], None], settings: SettingsState):
        super().__init__(close_window)
        self.settings_state = settings
        self.unsaved_settings = copy.deepcopy(settings.value)

    def render(self, time: float, frame_time: float):
        imgui.set_next_window_size_constraints(
            (400, 200),
            (imgui.FLT_MAX, imgui.FLT_MAX)
        )
        window_flags = imgui.WindowFlags_.menu_bar.value
        with imgui_ctx.begin("Settings", True, window_flags) as (expanded, opened):
            if not opened:
                self.close_window()

            with imgui_ctx.begin_menu_bar():
                clicked, _ = imgui.menu_item("Save", "", False, self.unsave)
                if clicked:
                    self.settings_state.value = self.unsaved_settings
                    save_settings(self.unsaved_settings)
                    self.unsaved_settings = copy.deepcopy(
                        self.unsaved_settings)
                    self.unsave = False

                clicked, _ = imgui.menu_item("Reset to Default", "", False)
                if clicked:
                    self.unsaved_settings = Settings()
                    self.unsave = True

            # -------------------- Interface Settings -------------------- #

            imgui.push_item_width(-200)

            imgui_style = imgui.get_style()
            with imgui_ctx.begin_tab_bar("##settings_tab", imgui.TableFlags_.none.value):
                for tab_field in dataclasses.fields(self.unsaved_settings):
                    tab_field = getattr(self.unsaved_settings, tab_field.name)
                    tab_name = tab_field.disp_name
                    if imgui.begin_tab_item(tab_name)[0]:
                        for settings_field in dataclasses.fields(tab_field):
                            settings_field = getattr(
                                tab_field, settings_field.name)
                            if type(settings_field) is SettingsField:
                                text_width = imgui.calc_text_size(
                                    settings_field.disp_name).x
                                imgui.push_item_width(-text_width -
                                                      imgui_style.frame_padding.x)
                                if render_settings_field(settings_field):
                                    self.unsave = True
                                imgui.pop_item_width()
                        imgui.end_tab_item()

            imgui.pop_item_width()
