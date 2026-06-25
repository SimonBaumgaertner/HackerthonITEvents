from enum import Enum

class Kategorie(str, Enum):
    KI = "Künstliche Intelligenz"
    UI_UX = "UI/UX Design und Frontend"
    SOFTWARE = "Software Development"
    SECURITY = "IT und Security"
    ANFAENGER = "Anfänger / Einsteiger"
    FORTGESCHRITTEN = "Fortgeschritten"
    EXPERTE = "Experte / Profi"
    FACHVORTRAG = "Fachvorträge & Keynotes"
    WORKSHOP = "Workshops & Hackathons"
    NETWORKING = "Networking & Meetups"
    KARRIERE = "Karriere & Recruiting"
