import unittest
import datetime
from scripts.update_dates import parse_date_string, resolve_year, clean_event_name, determine_category

class TestUFParser(unittest.TestCase):
    def test_resolve_year(self):
        # Fall term month resolution
        self.assertEqual(resolve_year("December", "Fall 2026"), 2026)
        self.assertEqual(resolve_year("January", "Fall 2026"), 2027)
        # Spring term month resolution
        self.assertEqual(resolve_year("January", "Spring 2027"), 2027)
        self.assertEqual(resolve_year("October", "Spring 2027"), 2026)
        # Summer term month resolution
        self.assertEqual(resolve_year("May", "Summer A/C 2026"), 2026)

    def test_clean_event_name(self):
        self.assertEqual(clean_event_name("Honors Theses due to College Advising Offices1"), "Honors Theses due to College Advising Offices")
        self.assertEqual(clean_event_name("Degree Status Available (on ONE.UF4)"), "Degree Status Available (on ONE.UF)")
        self.assertEqual(clean_event_name("Some Event^1"), "Some Event")

    def test_determine_category(self):
        self.assertEqual(determine_category("Thanksgiving Break"), "Holiday")
        self.assertEqual(determine_category("Drop/Add Day"), "Registration")
        self.assertEqual(determine_category("Fee Payment Deadline"), "Financial")
        self.assertEqual(determine_category("Commencement Ceremony"), "Commencement")
        self.assertEqual(determine_category("Classes Begin"), "Academic")

    def test_parse_date_string(self):
        # Single Date
        self.assertEqual(parse_date_string("August 20", "Fall 2026"), ["2026-08-20"])
        # Range in same month
        self.assertEqual(parse_date_string("June 22 - 26", "Summer C 2026"), ["2026-06-22", "2026-06-23", "2026-06-24", "2026-06-25", "2026-06-26"])
        # Multi-month range
        self.assertEqual(parse_date_string("December 25 - January 1", "Fall 2026")[-1], "2027-01-01")
        # List and range
        self.assertEqual(parse_date_string("August 20, 21, 24 - 26", "Fall 2026"), ["2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25", "2026-08-26"])

if __name__ == '__main__':
    unittest.main()
