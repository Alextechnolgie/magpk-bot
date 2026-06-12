"""Constants for the MAGPK Schedule integration."""
import logging

DOMAIN = "magpk_schedule"
CONF_GROUP = "group"

SCHEDULE_URL = "https://magpk.ru/studentu/raspisanie-zanyatij"

LOGGER = logging.getLogger(__package__)

WEEKDAYS_RU = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}

LESSON_TIMES = {
    1: "08:00 – 09:35",
    2: "09:45 – 11:20",
    3: "11:35 – 13:10",
    4: "13:30 – 15:05",
    5: "15:15 – 16:50",
    6: "17:00 – 18:35",
    7: "18:40 – 20:15",
}
