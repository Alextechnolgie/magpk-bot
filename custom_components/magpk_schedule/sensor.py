"""Sensor platform for MAGPK Schedule integration."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_GROUP
from .__init__ import MagpkScheduleCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MAGPK Schedule sensors."""
    coordinator: MagpkScheduleCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            MagpkScheduleTodaySensor(coordinator),
            MagpkScheduleTomorrowSensor(coordinator),
            MagpkScheduleWeekSensor(coordinator),
        ]
    )


def format_schedule_for_speech(lessons: list[dict] | None) -> str:
    """Format the lessons list into a clean, spoken Russian text for Yandex Alice."""
    if lessons is None:
        return "Расписание на этот день ещё не опубликовано."
    if not lessons:
        return "Занятий нет, можно отдыхать."

    parts = []
    for lesson in lessons:
        num = lesson.get("pair_num", "")
        # Find the first digit in the period number (e.g., "1 пара" -> 1)
        digit_match = re.search(r"\d", num)
        num_word = "пара"
        if digit_match:
            num_val = int(digit_match.group())
            num_words = {
                1: "Первая",
                2: "Вторая",
                3: "Третья",
                4: "Четвертая",
                5: "Пятая",
                6: "Шестая",
                7: "Седьмая",
            }
            num_word = num_words.get(num_val, f"{num_val}-я") + " пара"

        subject = lesson.get("subject", "")
        time_str = lesson.get("time", "")
        teacher = lesson.get("teacher", "")
        room = lesson.get("room", "")

        lesson_speech = f"{num_word}"
        if time_str:
            # Format time ranges nicely for speech: "08:00 – 09:35" -> "с 08:00 до 09:35"
            spoken_time = time_str.replace("–", "до").replace("-", "до")
            lesson_speech += f" с {spoken_time}"

        lesson_speech += f", {subject}"

        if teacher:
            # Expose only the surname for a cleaner vocal report
            teacher_parts = teacher.split()
            teacher_clean = teacher_parts[0] if teacher_parts else teacher
            lesson_speech += f", преподаватель {teacher_clean}"

        if room:
            room_clean = room.replace("каб.", "кабинет").replace("Каб.", "кабинет").strip()
            if room_clean.isdigit():
                lesson_speech += f", кабинет {room_clean}"
            else:
                lesson_speech += f", {room_clean}"

        parts.append(lesson_speech)

    return ". ".join(parts) + "."


def format_schedule_for_text(lessons: list[dict] | None) -> str:
    """Format the lessons list into a readable multiline text for display cards."""
    if lessons is None:
        return "Расписание не найдено."
    if not lessons:
        return "Занятий нет."

    lines = []
    for lesson in lessons:
        num = lesson.get("pair_num", "")
        time_str = lesson.get("time", "")
        subject = lesson.get("subject", "")
        teacher = lesson.get("teacher", "")
        room = lesson.get("room", "")

        details = []
        if teacher:
            # Abbreviate teacher name: "Иванов Иван Иванович" -> "Иванов И.И."
            parts = teacher.split()
            if len(parts) >= 3:
                abbrev = f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
            elif len(parts) == 2:
                abbrev = f"{parts[0]} {parts[1][0]}."
            else:
                abbrev = teacher
            details.append(abbrev)
        if room:
            details.append(room)

        details_str = f" ({', '.join(details)})" if details else ""
        lines.append(f"{num} ({time_str}): {subject}{details_str}")

    return "\n".join(lines)


def format_schedule_for_markdown_week(data: dict[str, Any] | None) -> str:
    """Format 7 days of schedule into a beautiful markdown string for Home Assistant dashboard."""
    if not data:
        return "Нет данных."

    lines = []
    for i in range(7):
        day_info = data.get(f"day_{i}")
        if not day_info:
            continue

        date_str = day_info.get("date")
        day_name = day_info.get("day_name")
        lessons = day_info.get("lessons")

        # Display date format compact: e.g. "Понедельник (15.06)"
        display_date = date_str[:-5] if date_str and len(date_str) > 5 else date_str
        lines.append(f"### {day_name} ({display_date})")

        if lessons is None:
            lines.append("*Нет данных (расписание не опубликовано)*")
        elif not lessons:
            lines.append("*Занятий нет*")
        else:
            for lesson in lessons:
                num = lesson.get("pair_num", "")
                time_str = lesson.get("time", "")
                subject = lesson.get("subject", "")
                teacher = lesson.get("teacher", "")
                room = lesson.get("room", "")

                details = []
                if teacher:
                    parts = teacher.split()
                    abbrev = f"{parts[0]} {parts[1][0]}.{parts[2][0]}." if len(parts) >= 3 else teacher
                    details.append(abbrev)
                if room:
                    details.append(room)

                details_str = f" • *{', '.join(details)}*" if details else ""
                lines.append(f"- **{num}** ({time_str}): {subject}{details_str}")

        lines.append("")  # Spacer between days

    return "\n".join(lines).strip()


class MagpkScheduleBaseSensor(CoordinatorEntity[MagpkScheduleCoordinator], SensorEntity):
    """Base class for MAGPK Schedule sensors."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: MagpkScheduleCoordinator, schedule_type: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.schedule_type = schedule_type
        group = coordinator.group
        self._attr_unique_id = f"magpk_schedule_{group}_{schedule_type}"
        
        # Friendly entity names
        type_name_ru = "сегодня" if schedule_type == "today" else "завтра"
        self._attr_name = f"Расписание на {type_name_ru}"

    @property
    def _data(self) -> dict[str, Any] | None:
        """Retrieve target schedule data from coordinator."""
        if not self.coordinator.data:
            return None
            
        # Map today/tomorrow to day_0/day_1
        key = self.schedule_type
        if key == "today":
            key = "day_0"
        elif key == "tomorrow":
            key = "day_1"
            
        return self.coordinator.data.get(key)

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        data = self._data
        if not data:
            return "Нет данных"
        
        lessons = data.get("lessons")
        if lessons is None:
            return "Нет данных"
        if not lessons:
            return "Занятий нет"
        
        count = len(lessons)
        # Select Russian plural form for "пара"
        if count == 1:
            suffix = "пара"
        elif 2 <= count <= 4:
            suffix = "пары"
        else:
            suffix = "пар"
            
        return f"{count} {suffix}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self._data
        if not data:
            return {
                "group_name": self.coordinator.group,
                "date": None,
                "day_name": None,
                "lessons": None,
                "schedule_text": "Нет данных",
                "schedule_speech": "Расписание отсутствует.",
            }

        lessons = data.get("lessons")
        return {
            "group_name": self.coordinator.group,
            "date": data.get("date"),
            "day_name": data.get("day_name"),
            "lessons": lessons,
            "schedule_text": format_schedule_for_text(lessons),
            "schedule_speech": format_schedule_for_speech(lessons),
        }


class MagpkScheduleTodaySensor(MagpkScheduleBaseSensor):
    """Sensor for MAGPK Schedule today."""

    def __init__(self, coordinator: MagpkScheduleCoordinator) -> None:
        """Initialize the today sensor."""
        super().__init__(coordinator, "today")


class MagpkScheduleTomorrowSensor(MagpkScheduleBaseSensor):
    """Sensor for MAGPK Schedule tomorrow."""

    def __init__(self, coordinator: MagpkScheduleCoordinator) -> None:
        """Initialize the tomorrow sensor."""
        super().__init__(coordinator, "tomorrow")


class MagpkScheduleWeekSensor(CoordinatorEntity[MagpkScheduleCoordinator], SensorEntity):
    """Sensor for MAGPK Schedule for the week ahead."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-multiselect"

    def __init__(self, coordinator: MagpkScheduleCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        group = coordinator.group
        self._attr_unique_id = f"magpk_schedule_{group}_week"
        self._attr_name = "Расписание на неделю"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor (days with lessons)."""
        data = self.coordinator.data
        if not data:
            return "Нет данных"

        days_with_lessons = 0
        for i in range(7):
            day_info = data.get(f"day_{i}")
            if day_info and day_info.get("lessons"):
                days_with_lessons += 1

        # Select Russian plural form for "день"
        if days_with_lessons == 1:
            suffix = "день с парами"
        elif 2 <= days_with_lessons <= 4:
            suffix = "дня с парами"
        else:
            suffix = "дней с парами"

        return f"{days_with_lessons} {suffix}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self.coordinator.data
        if not data:
            return {
                "group_name": self.coordinator.group,
                "schedule_markdown": "Нет данных",
            }

        return {
            "group_name": self.coordinator.group,
            "schedule_markdown": format_schedule_for_markdown_week(data),
        }
