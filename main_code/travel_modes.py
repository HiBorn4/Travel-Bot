# travel_modes.py

TRAVEL_MODES = {
    "Bus": {
        "code": "B",
        "travel_class": {
            "AC": "BAC",
            "Non-AC": "BNC"
        },
        "booking_method": {
            "Company Booked": "3",
            "Self Booked": "1",
            "Others": "4"
        },
        "defaults": {
            "requires_ticket_method": True
        }
    },
    "Own Car": {
        "code": "O",
        "travel_class": {
            "Any Class": "*"
        },
        "booking_method": {
            "": ""
        },
        "defaults": {
            "requires_ticket_method": False
        }
    },
    "Company Arranged Car": {
        "code": "A",
        "travel_class": {
            "AC": "BAC",
            "Non-AC": "BNC"
        },
        "booking_method": {
            "Company Booked": "3"
        },
        "defaults": {
            "requires_ticket_method": True
        }
    },
    "Train": {
        "code": "T",
        "travel_class": {
            "First Class AC": "1A",
            "Two Tier AC": "2AC",
            "Three Tier AC": "3AC",
            "Chair Car": "CC",
            "Sleeper Class": "SL",
            "Air Conditioned": "AC",
            "First Class": "FC"
        },
        "booking_method": {
            "Company Booked": "3",
            "Self Booked": "1",
            "Others": "4"
        },
        "defaults": {
            "requires_ticket_method": True
        }
    }
}
