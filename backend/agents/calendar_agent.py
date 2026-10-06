import os
from datetime import datetime, timedelta
from typing import Optional
from agents.base import BaseAgent
from tools.base import Tool
from memory.db import add_calendar_event, get_calendar_events, delete_calendar_event

class CalendarAgent(BaseAgent):
    def __init__(self):
        super().__init__("CalendarAgent")
        self.register_tool(Tool("create_calendar_event", "Schedule a new calendar event with date, time, and details", self.create_calendar_event))
        self.register_tool(Tool("list_upcoming_events", "List upcoming calendar events and meetings", self.list_upcoming_events))
        self.register_tool(Tool("search_calendar_events", "Search scheduled events by keyword or topic", self.search_calendar_events))
        self.register_tool(Tool("delete_calendar_event", "Cancel or delete a scheduled calendar event", self.delete_calendar_event, high_risk=True))
        self.register_tool(Tool("export_calendar_ics", "Export a scheduled event as an .ics file for Outlook/Google Calendar", self.export_calendar_ics))

    def create_calendar_event(
        self, 
        title: str, 
        event_date: str, 
        event_time: str = "10:00 AM", 
        duration_minutes: int = 30, 
        description: str = "", 
        location: str = "", 
        **kwargs
    ) -> str:
        if not title or not event_date:
            raise ValueError("Event title and event_date (YYYY-MM-DD or readable date) are required.")

        event_id = add_calendar_event(
            title=title,
            event_date=event_date,
            event_time=event_time,
            duration_minutes=int(duration_minutes),
            description=description,
            location=location
        )
        return (
            f"Calendar Event Scheduled Successfully (Event ID #{event_id}):\n"
            f"- Title: {title}\n"
            f"- Date: {event_date}\n"
            f"- Time: {event_time} ({duration_minutes} mins)\n"
            f"- Description: {description or 'None'}\n"
            f"- Location: {location or 'None'}"
        )

    def list_upcoming_events(self, limit: int = 15, **kwargs) -> str:
        events = get_calendar_events(limit=int(limit))
        if not events:
            return "No scheduled calendar events found."
            
        lines = []
        for ev in events:
            lines.append(
                f"Event #{ev['id']}: [{ev['event_date']} @ {ev['event_time']}] '{ev['title']}' "
                f"({ev['duration_minutes']}m) - {ev.get('description', '')}"
            )
        return f"Upcoming Calendar Events ({len(events)}):\n" + "\n".join(lines)

    def search_calendar_events(self, query: str, **kwargs) -> str:
        if not query:
            raise ValueError("Query parameter is required.")
        events = get_calendar_events(limit=50)
        matches = [ev for ev in events if query.lower() in ev['title'].lower() or query.lower() in ev.get('description', '').lower()]
        
        if not matches:
            return f"No calendar events found matching '{query}'."
        lines = [f"Event #{ev['id']}: {ev['event_date']} {ev['event_time']} - {ev['title']}" for ev in matches]
        return f"Found {len(matches)} matching events:\n" + "\n".join(lines)

    def delete_calendar_event(self, event_id: int, **kwargs) -> str:
        success = delete_calendar_event(int(event_id))
        if success:
            return f"Successfully deleted calendar event #{event_id}."
        return f"Calendar event #{event_id} not found."

    def export_calendar_ics(self, title: str, event_date: str, event_time: str = "10:00", output_path: Optional[str] = None, **kwargs) -> str:
        home = os.path.expanduser("~")
        dest = output_path or os.path.join(home, "Desktop", f"{title.replace(' ', '_')}.ics")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI OS//CalendarAgent//EN
BEGIN:VEVENT
SUMMARY:{title}
DESCRIPTION:Scheduled by AI OS
DTSTART;VALUE=DATE-TIME:{event_date.replace('-', '')}T100000Z
DTEND;VALUE=DATE-TIME:{event_date.replace('-', '')}T110000Z
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        with open(dest, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        return f"Exported iCalendar file to: '{dest}'"
