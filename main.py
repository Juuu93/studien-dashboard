from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

# ======== Entity-Klassen ========

@dataclass
class Termin:
    titel: str
    datum: date

@dataclass
class Pruefungsleistung:
    note: Optional[float] = None     # None = noch keine Note
    status: str = "offen"            # "offen" | "bestanden" | "nicht bestanden"

@dataclass
class Modul:
    titel: str
    ects: int
    pruefungsleistung: Optional[Pruefungsleistung] = None  # 0..1
    termine: List[Termin] = field(default_factory=list)     # 0..*

    def add_termin(self, termin: Termin) -> None:
        self.termine.append(termin)

@dataclass
class Semester:
    nummer: int
    module: List[Modul] = field(default_factory=list)

    def add_modul(self, modul: Modul) -> None:
        self.module.append(modul)

@dataclass
class Studiengang:
    name: str
    semester: List[Semester] = field(default_factory=list)

    def add_semester(self, sem: Semester) -> None:
        self.semester.append(sem)

@dataclass
class Student:
    name: str
    matrikelnummer: str
    studiengang: Studiengang


# ======== Infrastruktur ========

class SpeicherManager:
    """Für jetzt: Testdaten im Code. Später: MySQL (gleiche Schnittstelle beibehalten)."""
    def load_student_by_matrikel(self, matrikel: str) -> Optional[Student]:
        data = self._testdata()
        return data.get(matrikel)

    @staticmethod
    def _testdata() -> dict[str, Student]:
        sg = Studiengang("Angewandte KI B.Sc.")
        for i in range(1, 7):
            sg.add_semester(Semester(nummer=i))

        # Beispielmodule in Sem 3
        m1 = Modul("Computer Vision", 5,
                   pruefungsleistung=Pruefungsleistung(note=2.0, status="bestanden"))
        m1.add_termin(Termin("Klausur", date(2025, 7, 1)))

        m2 = Modul("NLP Grundlagen", 5,
                   pruefungsleistung=Pruefungsleistung(note=3.0, status="bestanden"))
        m3 = Modul("Reinforcement Learning", 5,
                   pruefungsleistung=Pruefungsleistung(note=2.7, status="bestanden"))
        m4 = Modul("Statistik & Wahrscheinlichkeit", 5)
        m4.add_termin(Termin("Abgabe Fallstudie", date(2025, 7, 15)))
        m4.add_termin(Termin("Klausur", date(2025, 8, 1)))

        sg.semester[2].module.extend([m1, m2, m3, m4])  # Index 2 = Semester 3

        student = Student(name="Julian Hinze", matrikelnummer="IU14102835", studiengang=sg)
        return {student.matrikelnummer: student}

# ======== Controller ========

class DashboardController:
    def __init__(self, storage: SpeicherManager) -> None:
        self.storage = storage
        self.student: Optional[Student] = None

    def load(self, matrikel: str) -> bool:
        self.student = self.storage.load_student_by_matrikel(matrikel)
        return self.student is not None

    def semester_progress(self, ziel_semester: int = 6) -> tuple[int, int]:
        current = self._ermittle_aktuelles_semester()
        return current, ziel_semester

    def ects_progress(self, ziel_ects: int = 180) -> tuple[int, int]:
        ects_sum = 0
        for sem in self._sg().semester:
            for m in sem.module:
                if m.pruefungsleistung and m.pruefungsleistung.status == "bestanden":
                    ects_sum += m.ects
        return ects_sum, ziel_ects

    def notendurchschnitt(self) -> Optional[float]:
        noten: List[float] = []
        for sem in self._sg().semester:
            for m in sem.module:
                if m.pruefungsleistung and m.pruefungsleistung.note is not None:
                    noten.append(m.pruefungsleistung.note)
        if not noten:
            return None
        return round(sum(noten) / len(noten), 2)

    def notenliste(self) -> List[tuple[str, float]]:
        ergebnis = []
        for sem in self._sg().semester:
            for m in sem.module:
                if m.pruefungsleistung and m.pruefungsleistung.note is not None:
                    ergebnis.append((m.titel, m.pruefungsleistung.note))
        return ergebnis

    def aktuell_belegte_module(self) -> List[str]:
        sem = self._aktuelles_semester_objekt()
        return [m.titel for m in sem.module] if sem else []

    def kommende_termine(self) -> List[tuple[str, date]]:
        out: List[tuple[str, date]] = []
        today = date.today()
        for sem in self._sg().semester:
            for m in sem.module:
                for t in m.termine:
                    if t.datum >= today:
                        out.append((f"{t.titel} ({m.titel})", t.datum))
        return sorted(out, key=lambda x: x[1])

    # -- Helpers --
    def _sg(self) -> Studiengang:
        assert self.student is not None
        return self.student.studiengang

    def _ermittle_aktuelles_semester(self) -> int:
        nummern = [s.nummer for s in self._sg().semester if s.module]
        return max(nummern) if nummern else 1

    def _aktuelles_semester_objekt(self) -> Optional[Semester]:
        cur = self._ermittle_aktuelles_semester()
        for s in self._sg().semester:
            if s.nummer == cur:
                return s
        return None

# ======== CLI ========

def render_dashboard(ctrl: DashboardController) -> None:
    sem_cur, sem_max = ctrl.semester_progress()
    ects_cur, ects_max = ctrl.ects_progress()
    avg = ctrl.notendurchschnitt()
    noten = ctrl.notenliste()
    module = ctrl.aktuell_belegte_module()
    termine = ctrl.kommende_termine()

    print("\n=== Dashboard ===")
    print(f"Semester und ECTS: {sem_cur} / {sem_max}   |   {ects_cur} / {ects_max} ECTS")
    print(f"Notendurchschnitt: {'–' if avg is None else avg}")
    for titel, note in noten:
        print(f"  {titel}: {note}")
    print("\nAktuell belegte Module:")
    for t in module:
        print(f"  - {t}")
    print("\nTermine:")
    for beschr, d in termine:
        print(f"  - {beschr}: {d.strftime('%d.%m.%Y')}")
    print("==================\n")

if __name__ == "__main__":
    sm = SpeicherManager()
    ctrl = DashboardController(sm)
    matrikel = input("Matrikelnummer eingeben: ").strip()
    if ctrl.load(matrikel):
        print(f"Willkommen, {ctrl.student.name}!")
        render_dashboard(ctrl)
    else:
        print("Unbekannte Matrikelnummer.")