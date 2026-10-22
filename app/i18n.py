"""English/Hindi label dictionaries for the invoice and picking-sheet PDFs (see
app/templates/invoice.html and picking_sheet.html), plus the small font stack each language
needs. Only the static chrome — headers, column labels, boilerplate — is translated; customer
names, item names, and other record data are printed as stored regardless of language, since
they aren't ours to translate.
"""

SUPPORTED_LANGS = ("en", "hi")

_INVOICE_EN = {
    "draft_banner": "Draft preview — this PO has not been converted to a sale bill yet",
    "doc_title": "Tax Invoice",
    "original_for_recipient": "Original for recipient",
    "billed_to": "Billed to",
    "invoice_details": "Invoice details",
    "invoice_no": "Invoice no.",
    "invoice_date": "Invoice date",
    "against_po": "Against PO",
    "place_of_supply": "Place of supply",
    "reverse_charge": "Reverse charge",
    "no": "No",
    "col_idx": "#",
    "col_item": "Item",
    "col_hsn": "HSN",
    "col_mrp": "MRP",
    "col_qty": "Qty",
    "col_rate": "Rate",
    "col_taxable": "Taxable",
    "col_gst": "GST",
    "col_cgst": "CGST",
    "col_sgst": "SGST",
    "col_total": "Total",
    "gst_summary_by_slab": "GST summary by slab",
    "col_slab": "Slab",
    "nil_rated": "nil rated",
    "amount_in_words": "Amount in words",
    "total_taxable_value": "Total taxable value",
    "round_off": "Round off",
    "invoice_total": "Invoice total",
    "payment": "Payment",
    "balance_due_nil": "balance due nil",
    "on_account": "On account · no UTR recorded",
    "added_to_balance": "added to customer balance due",
    "terms": (
        "Goods once sold are not returnable unless damaged in transit and reported within 24 hours.<br>"
        "Interest at 18% p.a. is chargeable on balances outstanding beyond 15 days.<br>"
        "Certified that the particulars given above are true and correct, and the amount indicated "
        "represents the price actually charged."
    ),
    "for_store": "For",
    "authorised_signatory": "Authorised signatory",
    "note_unlisted": "unlisted request · priced at billing",
    "note_inclusive": "inclusive of MRP · GST reverse-derived",
    "note_exclusive": "exclusive",
}

_INVOICE_HI = {
    "draft_banner": "प्रारूप पूर्वावलोकन — यह पीओ अभी तक बिक्री बिल में परिवर्तित नहीं हुआ है",
    "doc_title": "कर चालान",
    "original_for_recipient": "प्राप्तकर्ता के लिए मूल प्रति",
    "billed_to": "बिल प्राप्तकर्ता",
    "invoice_details": "चालान विवरण",
    "invoice_no": "चालान संख्या",
    "invoice_date": "चालान दिनांक",
    "against_po": "पीओ क्रमांक",
    "place_of_supply": "आपूर्ति का स्थान",
    "reverse_charge": "रिवर्स चार्ज",
    "no": "नहीं",
    "col_idx": "क्र.",
    "col_item": "वस्तु",
    "col_hsn": "एचएसएन",
    "col_mrp": "एमआरपी",
    "col_qty": "मात्रा",
    "col_rate": "दर",
    "col_taxable": "कर योग्य",
    "col_gst": "जीएसटी",
    "col_cgst": "सीजीएसटी",
    "col_sgst": "एसजीएसटी",
    "col_total": "कुल",
    "gst_summary_by_slab": "स्लैब अनुसार जीएसटी सारांश",
    "col_slab": "स्लैब",
    "nil_rated": "शून्य दर",
    "amount_in_words": "राशि शब्दों में",
    "total_taxable_value": "कुल कर योग्य राशि",
    "round_off": "राउंड ऑफ",
    "invoice_total": "कुल चालान राशि",
    "payment": "भुगतान",
    "balance_due_nil": "कोई शेष राशि नहीं",
    "on_account": "उधार खाते में · कोई यूटीआर दर्ज नहीं",
    "added_to_balance": "ग्राहक के खाते में जोड़ा गया",
    "terms": (
        "बेचा गया सामान वापस नहीं लिया जाएगा, जब तक कि वह परिवहन के दौरान क्षतिग्रस्त न हुआ हो और "
        "24 घंटे के भीतर सूचित न किया गया हो।<br>"
        "15 दिनों से अधिक बकाया राशि पर 18% वार्षिक ब्याज देय होगा।<br>"
        "प्रमाणित किया जाता है कि ऊपर दिए गए विवरण सही और सत्य हैं, तथा दर्शाई गई राशि वास्तव में "
        "वसूली गई राशि है।"
    ),
    "for_store": "हेतु",
    "authorised_signatory": "अधिकृत हस्ताक्षरकर्ता",
    "note_unlisted": "असूचीबद्ध अनुरोध · बिलिंग पर मूल्य निर्धारित",
    "note_inclusive": "एमआरपी सहित · जीएसटी प्रतिवर्ती रूप से निकाला गया",
    "note_exclusive": "कर अतिरिक्त",
}

_PICKING_EN = {
    "doc_title": "Picking Sheet",
    "not_tax_doc": "Not a tax document · warehouse copy",
    "received": "received",
    "stat_lines": "Lines",
    "stat_total_pieces": "Total pieces",
    "stat_aisles": "Aisles touched",
    "stat_unlisted": "Unlisted",
    "col_idx": "#",
    "col_item": "Item",
    "col_size": "Size",
    "col_aisle": "Aisle",
    "col_case": "Case",
    "col_qty": "Qty",
    "col_picked": "Picked",
    "shortages": "Shortages and substitutions",
    "picked_by": "Picked by",
    "checked_by": "Checked by",
    "received_by": "Received by (customer)",
    "note_unlisted": "unlisted · substitute if unavailable",
}

_PICKING_HI = {
    "doc_title": "पिकिंग शीट",
    "not_tax_doc": "यह कर दस्तावेज़ नहीं है · गोदाम प्रति",
    "received": "प्राप्त",
    "stat_lines": "पंक्तियां",
    "stat_total_pieces": "कुल इकाइयां",
    "stat_aisles": "छुई गई पंक्तियां",
    "stat_unlisted": "असूचीबद्ध",
    "col_idx": "क्र.",
    "col_item": "वस्तु",
    "col_size": "आकार",
    "col_aisle": "पंक्ति",
    "col_case": "केस",
    "col_qty": "मात्रा",
    "col_picked": "उठाया गया",
    "shortages": "कमी व विकल्प",
    "picked_by": "द्वारा उठाया गया",
    "checked_by": "द्वारा जांचा गया",
    "received_by": "द्वारा प्राप्त (ग्राहक)",
    "note_unlisted": "असूचीबद्ध · उपलब्ध न होने पर विकल्प दें",
}

# Font stack handed to the templates' CSS: WeasyPrint/Pango needs a Devanagari-capable face for
# Hindi, so the Hindi stack leads with Noto Sans Devanagari (installed via the Dockerfile) and
# keeps the Latin brand font for numerals/mono figures that stay in the Latin script either way.
_FONT_STACK = {
    "en": '"Archivo", "Helvetica Neue", Arial, sans-serif',
    "hi": '"Noto Sans Devanagari", "Archivo", "Helvetica Neue", Arial, sans-serif',
}


def normalize_lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"


def invoice_strings(lang: str) -> dict:
    return _INVOICE_HI if normalize_lang(lang) == "hi" else _INVOICE_EN


def picking_strings(lang: str) -> dict:
    return _PICKING_HI if normalize_lang(lang) == "hi" else _PICKING_EN


def font_stack(lang: str) -> str:
    return _FONT_STACK.get(normalize_lang(lang), _FONT_STACK["en"])
