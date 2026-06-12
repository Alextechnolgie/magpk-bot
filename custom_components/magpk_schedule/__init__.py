"""Initialisation of the MAGPK Schedule integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_GROUP, SCHEDULE_URL, LOGGER, WEEKDAYS_RU


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MAGPK Schedule from a config entry."""
    group = entry.data[CONF_GROUP]

    coordinator = MagpkScheduleCoordinator(hass, group)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["sensor"]):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class MagpkScheduleCoordinator(DataUpdateCoordinator[dict[str, any]]):
    """Class to manage fetching MAGPK schedule data."""

    def __init__(self, hass: HomeAssistant, group: str) -> None:
        """Initialize the coordinator."""
        self.group = group
        self._cache: dict[str, tuple[float, list[dict] | None]] = {}  # Cache date_iso -> (timestamp, lessons)
        super().__init__(
            hass,
            LOGGER,
            name=f"MAGPK Schedule for {group}",
            update_interval=timedelta(minutes=30),  # Update every 30 minutes
        )

    def _get_mgn_now(self) -> datetime:
        """Get current time in Magnitogorsk (GMT+5)."""
        tz = timezone(timedelta(hours=5))
        return datetime.now(tz)

    async def _async_update_data(self) -> dict[str, any]:
        """Fetch schedule data for the next 7 days from magpk.ru."""
        mgn_now = self._get_mgn_now()
        today = mgn_now.date()
        
        data = {}
        import time
        now_ts = time.time()

        for i in range(7):
            target_date = today + timedelta(days=i)
            date_iso = target_date.isoformat()

            # Check cache (1 hour TTL)
            cached_entry = self._cache.get(date_iso)
            if cached_entry and (now_ts - cached_entry[0] < 3600):
                lessons = cached_entry[1]
                LOGGER.info("Using cached lessons for %s: %s", date_iso, len(lessons) if lessons else 0)
            else:
                try:
                    lessons = await self._fetch_lessons_for_date(target_date)
                    self._cache[date_iso] = (now_ts, lessons)
                except Exception as e:
                    LOGGER.warning("Error fetching schedule for %s: %s", date_iso, e)
                    # Use expired cache if network fails, otherwise None
                    lessons = cached_entry[1] if cached_entry else None

            day_key = f"day_{i}"
            data[day_key] = {
                "date": target_date.strftime("%d.%m.%Y"),
                "day_name": WEEKDAYS_RU[target_date.weekday()],
                "lessons": lessons,
            }

        # Cleanup old cache entries
        if len(self._cache) > 30:
            active_dates = {(today + timedelta(days=d)).isoformat() for d in range(7)}
            for k in list(self._cache.keys()):
                if k not in active_dates:
                    del self._cache[k]

        return data


    async def _fetch_lessons_for_date(self, target_date: datetime.date) -> list[dict] | None:
        """Fetch lessons for a specific date."""
        date_str = target_date.strftime("%Y-%m-%d")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": SCHEDULE_URL,
        }

        # Use a local aiohttp session to manage cookies cleanly
        # To bypass SSL verification issues (same as bot's ssl_ctx.verify_mode = ssl.CERT_NONE)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                # 1. GET request to obtain session cookies
                async with session.get(SCHEDULE_URL, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        LOGGER.warning("Failed to load schedule page (GET): status %s", response.status)
                        return None
                    await response.text()

                # 2. POST request with the form payload to get the group schedule
                payload = {
                    "uch_gr_html": self.group,
                    "date_sch_html": date_str,
                    "btn_schedule_html": "Расписание",
                }
                async with session.post(SCHEDULE_URL, data=payload, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        LOGGER.warning("Failed to fetch schedule data (POST): status %s", response.status)
                        return None
                    html = await response.text()
            except Exception as e:
                LOGGER.error("Network error fetching schedule for %s on %s: %s", self.group, date_str, e)
                return None

        # Parse HTML content
        try:
            return self._parse_schedule_html(html, target_date)
        except Exception as e:
            LOGGER.error("Parsing error for %s on %s: %s", self.group, date_str, e)
            return None

    def _clean_hall(self, hall_str: str) -> str:
        """Remove long department names from classroom string."""
        prefixes = [
            "Машиностроительное отделение /",
            "технологическое отделения /",
            "общеобразовательное отделение /",
            "Технологическое отделение /",
            "Общеобразовательное отделение /",
        ]
        for prefix in prefixes:
            hall_str = hall_str.replace(prefix, "")
        return hall_str.strip()

    def _parse_schedule_html(self, html: str, target_date: datetime.date) -> list[dict] | None:
        """Parse the HTML response for lessons."""
        soup = BeautifulSoup(html, "html.parser")
        timetable_div = soup.find("div", class_="timetable")

        if not timetable_div:
            body_text = soup.get_text(" ", strip=True).lower()
            if "занятий нет" in body_text or "нет занятий" in body_text or "выходной" in body_text:
                return []  # No lessons (day off)
            return None  # No schedule data available

        # Check date mismatch in the parsed header to avoid yesterday's schedule
        expected_date_str = target_date.strftime("%d.%m.%Y")
        timetable_text = timetable_div.get_text(" ", strip=True)
        if expected_date_str not in timetable_text:
            LOGGER.info("Date mismatch in schedule HTML (got: %s, expected: %s). Website may have outdated data.", timetable_text[:50], expected_date_str)
            return None

        periods = timetable_div.find_all("ul", class_="timetable__period")
        if not periods:
            return []

        lessons = []
        for period in periods:
            num_tag = period.find("li", class_="timetable__item--period-num")
            num_str = num_tag.get_text(strip=True) if num_tag else "Пара"

            period_details = period.find("div", class_="period")
            if not period_details:
                continue

            time_tag = period_details.find("span", class_="period__time")
            disciple_tag = period_details.find("span", class_="period__disciple")
            teacher_tag = period_details.find("span", class_="period__teacher")
            hall_tag = period_details.find("span", class_="period__lecturehall")

            time_str = time_tag.get_text(strip=True) if time_tag else ""
            disciple_str = disciple_tag.get_text(strip=True) if disciple_tag else ""
            teacher_str = teacher_tag.get_text(strip=True) if teacher_tag else ""
            hall_str = hall_tag.get_text(strip=True) if hall_tag else ""

            if disciple_str:
                lessons.append({
                    "pair_num": num_str,
                    "time": time_str,
                    "subject": disciple_str,
                    "teacher": teacher_str,
                    "room": self._clean_hall(hall_str),
                })

        return lessons
