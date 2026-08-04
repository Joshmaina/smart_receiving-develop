import frappe

def setup_bevali_vat():
    company = "Bevali Online"
    abbr = "BO"

    print("=== 1. Checking Duties and Taxes Parent Account ===")
    parent_account = frappe.db.get_value(
        "Account",
        {"account_name": "Duties and Taxes", "company": company},
        "name"
    )
    if not parent_account:
        parent_account = frappe.db.get_value(
            "Account",
            {"account_name": "Current Liabilities", "company": company},
            "name"
        )
    print(f"Parent Account: {parent_account}")

    print("=== 2. Creating VAT Control Account ===")
    vat_account_name = f"VAT Control - {abbr}"
    if not frappe.db.exists("Account", vat_account_name):
        acc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "VAT Control",
            "parent_account": parent_account,
            "company": company,
            "root_type": "Liability",
            "account_type": "Tax",
            "currency": "KES",
            "is_group": 0
        })
        acc.insert(ignore_permissions=True)
        print(f"Created Account: {acc.name}")
    else:
        print(f"Account already exists: {vat_account_name}")

    print("=== 3. Creating Tax Categories ===")
    for cat in ["Sales", "Purchase"]:
        if not frappe.db.exists("Tax Category", cat):
            doc = frappe.get_doc({
                "doctype": "Tax Category",
                "title": cat
            })
            doc.insert(ignore_permissions=True)
            print(f"Created Tax Category: {cat}")
        else:
            print(f"Tax Category exists: {cat}")

    print("=== 4. Creating Sales Taxes and Charges Template ===")
    sales_template_name = f"Sales VAT 16% - {abbr}"
    if not frappe.db.exists("Sales Taxes and Charges Template", sales_template_name):
        doc = frappe.get_doc({
            "doctype": "Sales Taxes and Charges Template",
            "title": "Sales VAT 16%",
            "company": company,
            "tax_category": "Sales",
            "currency": "KES",
            "is_default": 1,
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": vat_account_name,
                "rate": 16.0,
                "description": "VAT 16%",
                "included_in_print_rate": 1
            }]
        })
        doc.insert(ignore_permissions=True)
        print(f"Created Sales Template: {doc.name}")
    else:
        print(f"Sales Template exists: {sales_template_name}")

    print("=== 5. Creating Purchase Taxes and Charges Template ===")
    purchase_template_name = f"Purchase VAT 16% - {abbr}"
    if not frappe.db.exists("Purchase Taxes and Charges Template", purchase_template_name):
        doc = frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": "Purchase VAT 16%",
            "company": company,
            "tax_category": "Purchase",
            "currency": "KES",
            "is_default": 1,
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": vat_account_name,
                "rate": 16.0,
                "description": "Input VAT 16%",
                "included_in_print_rate": 1,
                "add_deduct_tax": "Add"
            }]
        })
        doc.insert(ignore_permissions=True)
        print(f"Created Purchase Template: {doc.name}")
    else:
        print(f"Purchase Template exists: {purchase_template_name}")

    print("=== 6. Creating Item Tax Templates ===")
    item_templates = [
        {"title": "V", "rate": 16.0},
        {"title": "E", "rate": 0.0},
        {"title": "Z", "rate": 0.0}
    ]
    for item_t in item_templates:
        full_name = f"{item_t['title']} - {abbr}"
        if not frappe.db.exists("Item Tax Template", full_name):
            doc = frappe.get_doc({
                "doctype": "Item Tax Template",
                "title": item_t["title"],
                "company": company,
                "taxes": [{
                    "tax_type": vat_account_name,
                    "tax_rate": item_t["rate"]
                }]
            })
            doc.insert(ignore_permissions=True)
            print(f"Created Item Tax Template: {doc.name}")
        else:
            print(f"Item Tax Template exists: {full_name}")

    frappe.db.commit()
    print("=== VAT SETUP COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    setup_bevali_vat()
