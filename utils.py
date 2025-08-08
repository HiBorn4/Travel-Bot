prompt_hotel = """
You are a hotel bill expert. Extract and return structured JSON from this document.

{
  "hotel_name": "",
  "gst_number": "",
  "bill_number": "",
  "check_in": {
    "date": "",
    "time": "" this is the arrival time which will be near arrival date
  },
  "check_out": {
    "date": "", it is also called departure date
    "time": "" and time will be near departure date
  },
  "bill_date": "", usually "Bill Date" will be mentioned but if it is not there then use the date of departure
  "location": "", search for city/town name in the document
  "room_tariff": { information about this will be named Tarrif or Room Tariff which is basically the room charges so the number wont be small it would be in thousands.
    "amount_with_gst": "", add the gst amount to the room tariff (hack would be take the base room tariff and add 12% of it to it)
    "sac_code": "", this will be mentioned in the document as SAC Code or HSN Code if there are multiple tarrif the codes will be same so you can take the first one
    "gst_percent": "", usually tariff will be mentioned in CGST and SGST format so you can add them up usually it is 12% divided into 6% CGST and 6% SGST
    "tax_code": "", search if there is any tax code mentioned in the document
    "gst_amount": "", this will be 12% of the base room tariff
    "amount_without_gst": "" base room tariff without gst
  },
  "food_charges": { information about this will be named as ROOM SERVICE or FOOD CHARGES or FOOD BILL
    "amount_with_gst": "", add the gst amount to the food charges (hack would be take the base food charges and add 5% of it to it), there could be multilple food charges so you can add them up
    "sac_code": "",this will be mentioned in the document as SAC Code or HSN Code if there are multiple tarrif the codes will be same so you can take the first one
    "gst_percent": "",usually gst will be mentioned in CGST and SGST format so you can add them up usually it is 5% divided into 2.5% CGST and 2.5% SGST
    "tax_code": "",search if there is any tax code mentioned in the document
    "gst_amount": "",this will be 5% of the base food charges
    "amount_without_gst": ""base food charges without gst
  },
  "laundry_charges": { information about this will be named as LAUNDRY CHARGES or LAUNDRY BILL or LAUNDRY SERVICE or LAUNDRY
    "amount_with_gst": "", add the gst amount to the laundry charges (hack would be take the base laundry charges and add 18% of it to it), there could be multiple laundry charges so you can add them up
    "sac_code": "",this will be mentioned in the document as SAC Code or HSN Code if there are multiple tarrif the codes will be same so you can take the first one
    "gst_percent": "", usually gst will be mentioned in CGST and SGST format so you can add them up usually it is 18% divided into 9% CGST and 9% SGST
    "tax_code": "", search if there is any tax code mentioned in the document
    "gst_amount": "", this will be 18% of the base laundry charges
    "amount_without_gst": "" base laundry charges without gst
  },
  "other_charges": { If anything doesnt fall under the above categories then it will be mentioned as other charges or miscellaneous charges
    "amount_with_gst": "", add the gst amount to the other charges (hack would be take the base other charges and add 18% of it to it), there could be multiple other charges so you can add them up
    "sac_code": "",this will be mentioned in the document as SAC Code or HSN Code if there are multiple tarrif the codes will be same so you can take the first one
    "gst_percent": "", 
    "tax_code": "",
    "gst_amount": "",
    "amount_without_gst": ""
  },
  "claim_amount": ""
}
"""







prompt_food = """

INSTRUCTIONS
1. Return **ONLY** valid JSON (no extra commentary).
2. All monetary values must be numbers (without currency symbols).
3. If any field is missing, use the fallback values shown below.
4. Infer the meal type from the **time stamp** on the receipt:
   - 05:00 – 11:00  → breakfast  
   - 11:01 – 16:30  → lunch  
   - 16:31 – 23:00  → dinner  
   - Outside these ranges or missing → “Food type not found”
5. Location: pick the city/town mentioned (e.g., Pune, Mumbai, Chakan, Jodhpur).  
   If none → “Location not found”.
6. Receipt date: use the date printed on the receipt (dd-mm-yyyy).  
   If absent → “Receipt Data not found”.

OUTPUT JSON FORMAT
{
  "reimbursement_type": "Food",
  "claim_amount": <number>,
  "eligible_amount": <number>,
  "narration": "Food",
  "documents": 1,
  "location": "<city or fallback>",
  "receipt_date": "<dd-mm-yyyy or fallback>",
  "food_type": "<breakfast|lunch|dinner|fallback>"
}

EXAMPLE INPUT
Hotel Taj Blue Diamond
Invoice No: 12345
Pune – 411001
Date: 27-03-2024
Time: 13:45
Food & Beverages
Item                Qty    Amount
Paneer Tikka         1     320.00
Butter Naan          2     180.00
Masala Chaas         1      80.00
GST (5%)                    29.00
Total                      609.00

EXAMPLE OUTPUT
{
  "reimbursement_type": "Food",
  "claim_amount": 609,
  "eligible_amount": 609,
  "narration": "Food",
  "documents": 1,
  "location": "Pune",
  "receipt_date": "27-03-2024",
  "food_type": "lunch"
}
"""







prompt_travel = """You are an expert travel-ticket OCR parser.  
Extract every meaningful detail from the document and return **only** valid JSON.

INSTRUCTIONS
1. Return **ONLY** valid JSON (no extra commentary).
1. Return strictly valid JSON; no extra text or markdown fences.
2. All monetary values: plain numbers (no currency symbols, commas, or words).
3. Distance: numeric value in **kilometres** (omit “km” or commas).  
   If not stated, keep empty string "".
4. Date: use **dd-mm-yyyy** format.  
   If missing, return "".
5. Mode: choose from  
   ["Flight", "Train", "Bus", "Cab", "Bike", "Personal Vehicle", "Metro", "Ferry"]  
   (case-sensitive).  
   If unclear, use "Other".
6. Narration: auto-generate a concise description in the form  
   **"Mode from from_location to to_location"**.  
   Example: "Flight from Bengaluru to Delhi".
7. Documents: always 1 unless the image shows multiple distinct tickets, then use actual count.
8. Locations: use city names only (strip station/airport qualifiers unless they disambiguate).

OUTPUT JSON TEMPLATE
{
  "reimbursement_type": "Travel",
  "claim_amount": <number or "">,
  "eligible_amount": <number or "">,
  "narration": "<auto-generated string>",
  "documents": <1 by default>,
  "date": "<dd-mm-yyyy or "">,
  "from_location": "<city or "">,
  "to_location": "<city or "">,
  "mode": "<mode or "Other">",
  "distance": <number or "">
}

EXAMPLE INPUT
BOARDING PASS
Name: A Sharma
Flight 6E 2345
Date: 04-Aug-2025
Bengaluru (BLR) → Mumbai (BOM)
Total Paid: ₹7,890

EXAMPLE OUTPUT
{
  "reimbursement_type": "Travel",
  "claim_amount": 7890,
  "eligible_amount": 7890,
  "narration": "Flight from Bengaluru to Mumbai",
  "documents": 1,
  "date": "04-08-2025",
  "from_location": "Bengaluru",
  "to_location": "Mumbai",
  "mode": "Flight",
  "distance": ""
}
"""


