# ERPNext VAT Setup Handover – Bevali Online

## 1. Purpose of this document

This document explains exactly how VAT was configured in the Bevali Online ERPNext system and how it was connected to:

- Sales Invoices
- Purchase Invoices
- POS Awesome
- Customers
- Suppliers
- Items
- Item tax classifications

The purpose is to allow another AI agent or ERPNext implementer to understand the design and reproduce it correctly.

---

## 2. System context

The VAT setup was created for:

- **Company:** Bevali Online
- **Company abbreviation:** BO
- **Currency:** KES
- **ERPNext version:** Version 15
- **Main sales location:** Zion Mall - BO
- **Main store/purchasing warehouse:** Rupa - BO
- **Standard VAT rate:** 16%
- **Pricing method:** VAT-inclusive prices

The setup supports three common item tax classifications:

1. Standard-rated items at 16%
2. VAT-exempt items
3. Zero-rated items

---

## 3. Important design decision

We decided to use **one VAT control account** for both sales VAT and purchase VAT.

The account is:

> VAT Control - BO

This means:

- VAT charged on sales is credited to VAT Control - BO.
- VAT paid on purchases is debited to VAT Control - BO.
- The balance of the account represents the net VAT position before other adjustments.

We did **not** use separate Input VAT and Output VAT ledger accounts.

### Why this works

For a sales transaction:

- Sales income is credited.
- VAT Control - BO is credited with output VAT.
- Customer or cash account is debited with the total invoice amount.

For a purchase transaction:

- Expense or stock account is debited.
- VAT Control - BO is debited with input VAT.
- Supplier account is credited with the total invoice amount.

The single control account therefore carries the net difference between output VAT and recoverable input VAT.

---

# PART A – CREATE THE VAT LEDGER ACCOUNT

## 4. Create the VAT Control account

Go to:

> Accounting > Chart of Accounts

Open the chart for:

> Bevali Online

Create the following account:

| Field | Value |
|---|---|
| Account Name | VAT Control |
| Full account name after saving | VAT Control - BO |
| Parent Account | Duties and Taxes - BO |
| Root Type | Liability |
| Account Type | Tax |
| Company | Bevali Online |
| Currency | KES |
| Is Group | No |

Depending on the Chart of Accounts structure, the parent may appear under:

> Current Liabilities > Duties and Taxes - BO

### Important

The account must be a ledger account, not a group account.

The **Account Type must be Tax**.

Do not use the Sales account, Purchase account, Stock account, or Expense account as the VAT ledger.

---

# PART B – CREATE TAX CATEGORIES

## 5. Create the Sales Tax Category

Search for:

> Tax Category

Create:

| Field | Value |
|---|---|
| Tax Category Name | Sales |
| Title | Sales |
| Disabled | No |

Save the record.

This category is used for customers, Sales Invoices, POS transactions, and sales tax templates.

---

## 6. Create the Purchase Tax Category

Create another Tax Category:

| Field | Value |
|---|---|
| Tax Category Name | Purchase |
| Title | Purchase |
| Disabled | No |

Save the record.

This category is used for suppliers, Purchase Invoices, and purchase tax templates.

---

## 7. Why separate Tax Categories were necessary

Although both sales and purchases use the same VAT Control account, the Tax Categories tell ERPNext which template and item tax mapping to use.

The categories keep the transactions logically separate:

- **Sales** category for customer transactions
- **Purchase** category for supplier transactions

Do not assign the Purchase category to customers.

Do not assign the Sales category to suppliers.

---

# PART C – CREATE THE SALES VAT TEMPLATE

## 8. Create the Sales Taxes and Charges Template

Search for:

> Sales Taxes and Charges Template

Create a new template with these details:

| Field | Value |
|---|---|
| Title | Sales VAT 16% |
| Full saved name | Sales VAT 16% - BO |
| Company | Bevali Online |
| Tax Category | Sales |
| Currency | KES |
| Disabled | No |

Add one row in the Taxes and Charges table.

Recommended row configuration:

| Field | Value |
|---|---|
| Type | On Net Total |
| Account Head | VAT Control - BO |
| Rate | 16 |
| Description | VAT 16% |
| Included in Print Rate | Yes |
| Cost Center | Use the appropriate company or branch cost center if required |

Save the template.

### VAT-inclusive pricing

The **Included in Print Rate** checkbox is important because Bevali selling prices are VAT inclusive.

For example:

- Customer-facing price: KES 116
- Net sales value: KES 100
- VAT: KES 16
- Invoice total: KES 116

ERPNext extracts the VAT from the entered inclusive price instead of adding VAT on top.

---

# PART D – CREATE THE PURCHASE VAT TEMPLATE

## 9. Create the Purchase Taxes and Charges Template

Search for:

> Purchase Taxes and Charges Template

Create:

| Field | Value |
|---|---|
| Title | Purchase VAT 16% |
| Full saved name | Purchase VAT 16% - BO |
| Company | Bevali Online |
| Tax Category | Purchase |
| Currency | KES |
| Disabled | No |

Add one row in the Taxes and Charges table:

| Field | Value |
|---|---|
| Type | On Net Total |
| Account Head | VAT Control - BO |
| Rate | 16 |
| Description | Input VAT 16% |
| Included in Print Rate | Yes |
| Add or Deduct | Add |
| Cost Center | Use the appropriate company or branch cost center if required |

Save the template.

### Purchase pricing treatment

The purchase template was also configured as VAT inclusive.

Example:

- Supplier invoice total: KES 116
- Net purchase or stock value: KES 100
- Input VAT: KES 16
- Supplier payable: KES 116

ERPNext posts the KES 16 as a debit to VAT Control - BO.

---

# PART E – CREATE ITEM TAX TEMPLATES

## 10. Why Item Tax Templates were created

The main Sales and Purchase tax templates create the VAT calculation row on an invoice.

The Item Tax Templates tell ERPNext which tax rate applies to each individual item.

This is important because the shop may sell:

- Standard-rated items
- Exempt items
- Zero-rated items

Without Item Tax Templates, every item would normally use the main template rate.

---

## 11. Create the standard-rated Item Tax Template

Search for:

> Item Tax Template

Create:

| Field | Value |
|---|---|
| Title | V |
| Full saved name | V - BO |
| Company | Bevali Online |
| Disabled | No |

Add the tax row:

| Field | Value |
|---|---|
| Tax Type | VAT Control - BO |
| Tax Rate | 16 |

Save.

The letter **V** represents a normal VAT-rated item.

---

## 12. Create the exempt Item Tax Template

Create:

| Field | Value |
|---|---|
| Title | E |
| Full saved name | E - BO |
| Company | Bevali Online |
| Disabled | No |

Add the tax row:

| Field | Value |
|---|---|
| Tax Type | VAT Control - BO |
| Tax Rate | 0 |

Save.

The letter **E** represents a VAT-exempt item.

The tax rate is zero in ERPNext, but the business meaning is exempt.

---

## 13. Create the zero-rated Item Tax Template

Create:

| Field | Value |
|---|---|
| Title | Z |
| Full saved name | Z - BO |
| Company | Bevali Online |
| Disabled | No |

Add the tax row:

| Field | Value |
|---|---|
| Tax Type | VAT Control - BO |
| Tax Rate | 0 |

Save.

The letter **Z** represents a zero-rated item.

Although both E and Z currently use a zero rate in ERPNext, they are kept as separate templates because they have different tax-reporting meanings.

---

# PART F – CONNECT VAT TO ITEMS

## 14. Open an Item

Search for:

> Item

Open the item that needs VAT configuration.

Go to the item's tax section. Depending on the ERPNext form layout, this may be called:

- Taxes
- Item Tax
- Item Tax Templates

Add the correct Item Tax Template rows.

---

## 15. Standard-rated item setup

For a normal 16% VAT item, add:

| Tax Category | Item Tax Template |
|---|---|
| Sales | V - BO |
| Purchase | V - BO |

This ensures the item uses 16% VAT in both Sales Invoices and Purchase Invoices.

---

## 16. Exempt item setup

For an exempt item, add:

| Tax Category | Item Tax Template |
|---|---|
| Sales | E - BO |
| Purchase | E - BO |

---

## 17. Zero-rated item setup

For a zero-rated item, add:

| Tax Category | Item Tax Template |
|---|---|
| Sales | Z - BO |
| Purchase | Z - BO |

---

## 18. Item import approach used

For the full Bevali item master, the item tax mappings were added through Data Import.

The standard mapping used for most normal taxable items was:

- Tax Category: Sales
- Item Tax Template: V - BO
- Tax Category: Purchase
- Item Tax Template: V - BO

This was applied to thousands of existing items.

### Important Data Import warning

The two rows belong to the child table under each Item.

The import must not overwrite or remove other valid child-table rows accidentally.

Always test with a small number of items before updating the full item master.

---

# PART G – CONNECT VAT TO CUSTOMERS

## 19. Set Customer Tax Category

Open each Customer.

Set:

| Field | Value |
|---|---|
| Tax Category | Sales |

Save.

For new customers, use Sales as the normal customer Tax Category.

This helps ERPNext select the Sales VAT template when creating Sales Invoices.

---

## 20. Walk-in customer setup

The Bevali POS walk-in customer is:

> Zion WalkIn

Its Tax Category should be:

> Sales

This ensures POS sales are treated as sales transactions and use the correct tax setup.

---

# PART H – CONNECT VAT TO SUPPLIERS

## 21. Set Supplier Tax Category

Open each Supplier.

Set:

| Field | Value |
|---|---|
| Tax Category | Purchase |

Save.

For new suppliers, use Purchase as the normal Supplier Tax Category.

This helps ERPNext select the Purchase VAT template in Purchase Invoices.

---

# PART I – CONNECT VAT TO SALES INVOICES

## 22. Normal Sales Invoice setup

When creating a Sales Invoice, confirm:

| Field | Expected Value |
|---|---|
| Company | Bevali Online |
| Customer Tax Category | Sales |
| Taxes and Charges Template | Sales VAT 16% - BO |
| Item Tax Template | V - BO, E - BO, or Z - BO |
| Price List | The applicable selling price list |
| Prices | VAT inclusive |

For Bevali, the main selling price list was:

> Zion Retail Price

### What should happen

When a standard-rated item is added:

1. ERPNext reads the Sales Tax Category.
2. ERPNext loads Sales VAT 16% - BO.
3. ERPNext checks the item's Sales Item Tax Template.
4. The V - BO template applies 16%.
5. Because the tax is included in the print rate, VAT is extracted from the item price.
6. VAT is posted to VAT Control - BO after submission.

---

## 23. Test a Sales Invoice

Use a simple test item priced at KES 116 VAT inclusive.

Expected calculation:

| Component | Amount |
|---|---:|
| Gross selling price | 116.00 |
| Net sales value | 100.00 |
| VAT at 16% | 16.00 |
| Customer total | 116.00 |

After submitting, open:

> Accounting > General Ledger

Filter by:

- Voucher Type: Sales Invoice
- Voucher Number: the test invoice
- Account: VAT Control - BO

Expected VAT posting:

> Credit VAT Control - BO by KES 16

Also confirm the sales income account is credited with KES 100.

---

# PART J – CONNECT VAT TO POS AWESOME

## 24. POS Profile VAT configuration

The Bevali Zion Mall POS Profiles were configured with:

| Field | Value |
|---|---|
| Company | Bevali Online |
| Warehouse | Zion Mall - BO |
| Customer | Zion WalkIn |
| Tax Category | Sales |
| Taxes and Charges Template | Sales VAT 16% - BO |
| Price List | Zion Retail Price |
| Currency | KES |
| Income Account | Zion Mall Sales - BO |
| Expense Account | Zion Mall COGS - BO |

The Sales VAT template and Sales Tax Category must be selected in the POS Profile.

### POS Profiles used

Bevali had separate POS Profiles for different cashiers, including:

- Cashier 1
- Cashier 2
- Cashier 3

Each profile should use the same VAT configuration unless there is a valid business reason to differ.

---

## 25. Test POS VAT

Open a POS Awesome shift.

Add a normal standard-rated item with a VAT-inclusive selling price.

Before completing payment, check that:

- The total shown to the customer remains the selling price.
- VAT is not incorrectly added again on top.
- The tax amount appears in the invoice tax breakdown.
- The submitted Sales Invoice posts VAT to VAT Control - BO.

### Common POS problem

If the item price is KES 116 and POS displays KES 134.56, VAT is being added on top instead of extracted.

Check:

- Included in Print Rate is enabled.
- The correct tax template is selected.
- The POS Profile uses Sales VAT 16% - BO.
- There is no second VAT row or duplicate template.
- The item has the correct Item Tax Template.

---

# PART K – CONNECT VAT TO PURCHASE INVOICES

## 26. Purchase Invoice setup

When creating a Purchase Invoice, confirm:

| Field | Expected Value |
|---|---|
| Company | Bevali Online |
| Supplier Tax Category | Purchase |
| Taxes and Charges Template | Purchase VAT 16% - BO |
| Item Tax Template | V - BO, E - BO, or Z - BO |
| Prices | VAT inclusive where applicable |
| Supplier Invoice Number | Enter the supplier's invoice number |
| Bill Date | Enter the actual supplier invoice date |

For stock items, also confirm the correct warehouse, normally:

> Rupa - BO

---

## 27. What should happen on purchase

For a normal taxable item:

1. ERPNext reads the Supplier's Purchase Tax Category.
2. It loads Purchase VAT 16% - BO.
3. It reads the item's Purchase Item Tax Template.
4. V - BO applies the 16% rate.
5. VAT is extracted from the VAT-inclusive supplier rate.
6. On submission, input VAT is debited to VAT Control - BO.
7. The supplier is credited with the full invoice value.

---

## 28. Test a Purchase Invoice

Use a simple VAT-inclusive purchase of KES 116.

Expected calculation:

| Component | Amount |
|---|---:|
| Gross supplier invoice value | 116.00 |
| Net purchase or stock value | 100.00 |
| Input VAT at 16% | 16.00 |
| Supplier payable | 116.00 |

After submission, check the General Ledger.

Expected posting:

> Debit VAT Control - BO by KES 16

The stock or expense account should be debited with KES 100.

The supplier payable account should be credited with KES 116.

---

# PART L – VERIFY THE COMPLETE VAT FLOW

## 29. Sales verification checklist

For a submitted Sales Invoice, confirm:

- Tax Category is Sales.
- Sales VAT 16% - BO is selected.
- Standard item uses V - BO.
- Exempt item uses E - BO.
- Zero-rated item uses Z - BO.
- VAT is extracted from the inclusive price.
- VAT Control - BO receives a credit.
- Customer or cash is debited with the full invoice total.
- Sales income excludes the VAT portion.

---

## 30. Purchase verification checklist

For a submitted Purchase Invoice, confirm:

- Tax Category is Purchase.
- Purchase VAT 16% - BO is selected.
- The item's Purchase Item Tax Template is correct.
- VAT is extracted from the inclusive rate.
- VAT Control - BO receives a debit.
- The expense or stock value excludes VAT.
- Supplier payable equals the complete supplier invoice total.

---

## 31. General Ledger verification

Go to:

> Accounting > General Ledger

Use these filters:

- Company: Bevali Online
- Account: VAT Control - BO
- Date range: required period

The ledger should show:

- Credits from taxable sales
- Debits from taxable purchases
- Any manual VAT adjustments, if posted
- A running balance representing the net VAT position

Do not rely only on the invoice screen. Always verify the ledger entries after testing.

---

# PART M – IMPORTANT PITFALLS

## 32. Tax added twice

Symptoms:

- VAT-inclusive price becomes higher at checkout.
- A KES 116 item becomes KES 134.56.

Possible causes:

- Included in Print Rate is not checked.
- Two VAT rows exist.
- POS Profile and invoice have duplicate tax templates.
- A custom script is adding another tax row.
- The wrong template was selected.

---

## 33. No VAT is calculated

Possible causes:

- No Taxes and Charges Template is selected.
- Customer or Supplier has no Tax Category.
- Item has no Item Tax Template.
- Item Tax Template account does not match VAT Control - BO.
- Tax template is disabled.
- Tax Category on template does not match the transaction.
- Tax rate is zero because the item is using E - BO or Z - BO.

---

## 34. VAT posts to the wrong account

Possible causes:

- Sales or Purchase template uses an incorrect Account Head.
- Item Tax Template points to a different tax account.
- A copied template still references another company's account.
- The transaction belongs to another company.

All VAT rows should point to:

> VAT Control - BO

for Bevali Online.

---

## 35. Wrong Tax Category

Correct mapping:

| Document or Party | Tax Category |
|---|---|
| Customer | Sales |
| Sales Invoice | Sales |
| POS Profile | Sales |
| Supplier | Purchase |
| Purchase Invoice | Purchase |

Do not mix the two categories.

---

## 36. Wrong company suffix

ERPNext automatically applies company abbreviations to many account and template names.

For Bevali Online, confirm names end in:

> - BO

Do not accidentally select an account or template ending in an abbreviation for another company.

---

## 37. Item tax template and main tax template are both required

The main Sales or Purchase Taxes and Charges Template creates the tax calculation row on the invoice.

The Item Tax Template tells ERPNext the applicable item-specific rate.

They do not normally create duplicate VAT when configured correctly.

The Item Tax Template overrides or controls the tax rate for that item against the matching VAT account.

---

# PART N – IMPLEMENTATION ORDER FOR A NEW INSTANCE

## 38. Recommended sequence

When reproducing this setup in a new ERPNext company, follow this order:

1. Create or verify the company.
2. Create the VAT Control ledger account.
3. Create the Sales Tax Category.
4. Create the Purchase Tax Category.
5. Create the Sales VAT 16% Taxes and Charges Template.
6. Create the Purchase VAT 16% Taxes and Charges Template.
7. Create V, E, and Z Item Tax Templates.
8. Assign Tax Category Sales to customers.
9. Assign Tax Category Purchase to suppliers.
10. Add Sales and Purchase Item Tax Template rows to items.
11. Connect Sales VAT 16% to the POS Profiles.
12. Test one standard-rated Sales Invoice.
13. Test one exempt or zero-rated Sales Invoice.
14. Test one standard-rated Purchase Invoice.
15. Verify General Ledger postings.
16. Only after successful testing, use Data Import for bulk updates.

---

# PART O – EXACT BEVALI CONFIGURATION SUMMARY

## 39. Core records

| Record Type | Name |
|---|---|
| Company | Bevali Online |
| VAT Account | VAT Control - BO |
| Sales Tax Category | Sales |
| Purchase Tax Category | Purchase |
| Sales Template | Sales VAT 16% - BO |
| Purchase Template | Purchase VAT 16% - BO |
| Standard Item Tax Template | V - BO |
| Exempt Item Tax Template | E - BO |
| Zero-rated Item Tax Template | Z - BO |
| Main POS Customer | Zion WalkIn |
| Main POS Warehouse | Zion Mall - BO |
| Main Purchasing Warehouse | Rupa - BO |
| Selling Price List | Zion Retail Price |

---

## 40. Item mapping summary

### Standard taxable item

| Category | Template |
|---|---|
| Sales | V - BO |
| Purchase | V - BO |

### Exempt item

| Category | Template |
|---|---|
| Sales | E - BO |
| Purchase | E - BO |

### Zero-rated item

| Category | Template |
|---|---|
| Sales | Z - BO |
| Purchase | Z - BO |

---

# PART P – GUIDANCE FOR THE NEXT AI AGENT

## 41. Instructions to the implementation agent

Before making changes:

1. Take a full ERPNext backup including files.
2. Confirm the exact company and abbreviation.
3. Inspect the existing Chart of Accounts.
4. Check whether VAT Control - BO already exists.
5. Check whether the Tax Categories and templates already exist.
6. Do not create duplicate accounts or duplicate tax templates.
7. Test with one item, one customer, and one supplier first.
8. Verify the General Ledger before performing bulk imports.
9. Preserve VAT-inclusive pricing.
10. Do not separate input and output VAT accounts unless the business explicitly changes the current accounting design.

---

## 42. Definition of success

The VAT setup is working correctly when:

- A KES 116 VAT-inclusive sale posts KES 100 to Sales and KES 16 credit to VAT Control - BO.
- A KES 116 VAT-inclusive purchase posts KES 100 to Stock or Expense and KES 16 debit to VAT Control - BO.
- POS Awesome does not add VAT on top of the displayed retail price.
- Exempt and zero-rated items remain at zero VAT.
- Customer transactions use the Sales Tax Category.
- Supplier transactions use the Purchase Tax Category.
- The General Ledger shows correct VAT entries for both sales and purchases.

---

## 43. Final note

This document describes the exact VAT architecture used for Bevali Online.

For another ERPNext company, the same structure can be reused, but all company-specific names and suffixes must be changed. For example, replace `- BO` with the new company's abbreviation and confirm the correct warehouses, income accounts, expense accounts, cost centers, customers, suppliers, and price lists.
