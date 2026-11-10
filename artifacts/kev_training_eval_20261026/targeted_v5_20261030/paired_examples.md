# v5 成对样题审阅

以下标签由可见题面规则重算，配对题在同一个 split。不是官方测试题改数字。

## insufficient / overtime:False

### targeted-v5-20261030/insufficient/train/000197

SERVICE DESK NOTE
Monday through Thursday hours: [6, 6, 6, 6]. Payroll desk: Central.
APPLICABLE RULE
Overtime applies when total hours strictly exceed 35 in a Monday-to-Friday week. There is at most one shift per day, each between 0 and 10 hours inclusive. No weekend work occurs.

Does overtime apply to this week? Use only the supplied facts.

正确答案：The requirement is not satisfied

### targeted-v5-20261030/insufficient/train/000196

SERVICE DESK NOTE
Monday through Thursday hours: [6, 6, 6, 6]. Payroll desk: Central. Friday hours: 0.
APPLICABLE RULE
Overtime applies when total hours strictly exceed 35 in a Monday-to-Friday week. There is at most one shift per day, each between 0 and 10 hours inclusive. No weekend work occurs.

Does overtime apply to this week? Use only the supplied facts.

正确答案：The requirement is not satisfied

## insufficient / overtime:True

### targeted-v5-20261030/insufficient/train/000167

Overtime applies when total hours strictly exceed 38 in a Monday-to-Friday week. There is at most one shift per day, each between 0 and 10 hours inclusive. No weekend work occurs.
Case: Monday through Thursday hours: [8, 8, 8, 9]. Payroll desk: West. An unlisted field is not available; do not assume a default value.

Does overtime apply to this week? Use only the supplied facts.

正确答案：Cannot determine from the information given

### targeted-v5-20261030/insufficient/train/000166

Overtime applies when total hours strictly exceed 38 in a Monday-to-Friday week. There is at most one shift per day, each between 0 and 10 hours inclusive. No weekend work occurs.
Case: Monday through Thursday hours: [8, 8, 8, 9]. Payroll desk: West. An unlisted field is not available; do not assume a default value. Friday hours: 10.

Does overtime apply to this week? Use only the supplied facts.

正确答案：The requirement is satisfied

## insufficient / price_match:True

### targeted-v5-20261030/insufficient/train/000255

{'case': 'Our price: $500. Competitor price: $475. An unlisted field is not available; do not assume a default value.', 'policy': 'A price match qualifies if the identical item is in stock at the competitor and its price is strictly lower than ours by at most 10% of our price. Identity is verified; there are no other conditions.'}

Does this price match qualify? Use only the supplied facts.

正确答案：Cannot determine from the information given

### targeted-v5-20261030/insufficient/train/000254

{'case': 'Our price: $500. Competitor price: $475. An unlisted field is not available; do not assume a default value. Competitor inventory: out of stock.', 'policy': 'A price match qualifies if the identical item is in stock at the competitor and its price is strictly lower than ours by at most 10% of our price. Identity is verified; there are no other conditions.'}

Does this price match qualify? Use only the supplied facts.

正确答案：The requirement is not satisfied

## insufficient / warranty:True

### targeted-v5-20261030/insufficient/train/000205

SERVICE DESK NOTE
Claim received: 2028-05-19. Item serial: W80221.
APPLICABLE RULE
This warranty expires on 2028-08-06, inclusive. A claim by that date qualifies only for a manufacturing defect; accidental damage never qualifies. Every claim has exactly one of these causes. Claims after expiry do not qualify regardless of cause.

Is the claim covered? Use only the supplied facts.

正确答案：Cannot determine from the information given

### targeted-v5-20261030/insufficient/train/000204

SERVICE DESK NOTE
Claim received: 2028-05-19. Item serial: W80221. Technician confirmed cause: manufacturing defect.
APPLICABLE RULE
This warranty expires on 2028-08-06, inclusive. A claim by that date qualifies only for a manufacturing defect; accidental damage never qualifies. Every claim has exactly one of these causes. Claims after expiry do not qualify regardless of cause.

Is the claim covered? Use only the supplied facts.

正确答案：The requirement is satisfied

## insufficient / shipping:True

### targeted-v5-20261030/insufficient/train/000127

Shipping is free if merchandise subtotal minus discount is at least $100. The merchandise discount is between $0 and $60 inclusive. Ignore taxes and delivery fees in this calculation.
Case: Merchandise subtotal: $130. Tax: $8. An unlisted field is not available; do not assume a default value.

Does this order receive free shipping? Use only the supplied facts.

正确答案：Cannot determine from the information given

### targeted-v5-20261030/insufficient/train/000126

Shipping is free if merchandise subtotal minus discount is at least $100. The merchandise discount is between $0 and $60 inclusive. Ignore taxes and delivery fees in this calculation.
Case: Merchandise subtotal: $130. Tax: $8. An unlisted field is not available; do not assume a default value. Merchandise discount: $60.

Does this order receive free shipping? Use only the supplied facts.

正确答案：The requirement is not satisfied

## insufficient / return:True

### targeted-v5-20261030/insufficient/train/000012

Returns qualify if requested no more than 45 elapsed calendar days after delivery, inclusive. Every order below was delivered between its order date and its return request, inclusive. There are no other requirements.
Case: Order date: 2028-10-24. Return requested: 2028-12-16. Delivered: 2028-12-16.

Does this return qualify? Use only the supplied facts.

正确答案：The requirement is satisfied

### targeted-v5-20261030/insufficient/train/000013

Returns qualify if requested no more than 45 elapsed calendar days after delivery, inclusive. Every order below was delivered between its order date and its return request, inclusive. There are no other requirements.
Case: Order date: 2028-10-24. Return requested: 2028-12-16.

Does this return qualify? Use only the supplied facts.

正确答案：Cannot determine from the information given

## insufficient / approval:True

### targeted-v5-20261030/insufficient/train/000048

{'case': 'Amount: $1800. Actual approver: Leon. Copied colleague: Director Tessa, authority level 3. Leon has authority level 1.', 'policy': 'Payments below $150 require no approval. All other payments require an actual approver with authority level at least 2. Every approver has level 1, 2 or 3. A copied colleague is not an approver. Decide only whether authorization is sufficient.'}

Is the payment sufficiently authorized? Use only the supplied facts.

正确答案：The requirement is not satisfied

### targeted-v5-20261030/insufficient/train/000049

{'case': 'Amount: $1800. Actual approver: Leon. Copied colleague: Director Tessa, authority level 3.', 'policy': 'Payments below $150 require no approval. All other payments require an actual approver with authority level at least 2. Every approver has level 1, 2 or 3. A copied colleague is not an approver. Decide only whether authorization is sufficient.'}

Is the payment sufficiently authorized? Use only the supplied facts.

正确答案：Cannot determine from the information given

## insufficient / tenure:True

### targeted-v5-20261030/insufficient/train/000101

{'case': 'Leon transferred to the Support team on 2027-09-21.', 'policy': 'The benefit requires at least 365 elapsed days of continuous employment by 2028-08-12. Team transfers do not reset employment. The employee joined the company on or before the stated transfer date and has remained continuously employed through the application date.'}

Is the employee eligible for the benefit? Use only the supplied facts.

正确答案：Cannot determine from the information given

### targeted-v5-20261030/insufficient/train/000100

{'case': 'Leon transferred to the Support team on 2027-09-21. Company hire date: 2027-09-21.', 'policy': 'The benefit requires at least 365 elapsed days of continuous employment by 2028-08-12. Team transfers do not reset employment. The employee joined the company on or before the stated transfer date and has remained continuously employed through the application date.'}

Is the employee eligible for the benefit? Use only the supplied facts.

正确答案：The requirement is not satisfied

## insufficient / price_match:False

### targeted-v5-20261030/insufficient/train/000279

A price match qualifies if the identical item is in stock at the competitor and its price is strictly lower than ours by at most 15% of our price. Identity is verified; there are no other conditions.
Case: Our price: $500. Competitor price: $400. An unlisted field is not available; do not assume a default value.

Does this price match qualify? Use only the supplied facts.

正确答案：The requirement is not satisfied

### targeted-v5-20261030/insufficient/train/000278

A price match qualifies if the identical item is in stock at the competitor and its price is strictly lower than ours by at most 15% of our price. Identity is verified; there are no other conditions.
Case: Our price: $500. Competitor price: $400. An unlisted field is not available; do not assume a default value. Competitor inventory: out of stock.

Does this price match qualify? Use only the supplied facts.

正确答案：The requirement is not satisfied

## insufficient / approval:False

### targeted-v5-20261030/insufficient/train/000075

{'case': 'Amount: $29. Actual approver: Sana. Copied colleague: Director Tessa, authority level 3. An unlisted field is not available; do not assume a default value.', 'policy': 'Payments below $200 require no approval. All other payments require an actual approver with authority level at least 2. Every approver has level 1, 2 or 3. A copied colleague is not an approver. Decide only whether authorization is sufficient.'}

Is the payment sufficiently authorized? Use only the supplied facts.

正确答案：The requirement is satisfied

### targeted-v5-20261030/insufficient/train/000074

{'case': 'Amount: $29. Actual approver: Sana. Copied colleague: Director Tessa, authority level 3. An unlisted field is not available; do not assume a default value. Sana has authority level 3.', 'policy': 'Payments below $200 require no approval. All other payments require an actual approver with authority level at least 2. Every approver has level 1, 2 or 3. A copied colleague is not an approver. Decide only whether authorization is sufficient.'}

Is the payment sufficiently authorized? Use only the supplied facts.

正确答案：The requirement is satisfied

## insufficient / shipping:False

### targeted-v5-20261030/insufficient/train/000157

SERVICE DESK NOTE
Merchandise subtotal: $92. Tax: $6.
APPLICABLE RULE
Shipping is free if merchandise subtotal minus discount is at least $100. The merchandise discount is between $0 and $60 inclusive. Ignore taxes and delivery fees in this calculation.

Does this order receive free shipping? Use only the supplied facts.

正确答案：The requirement is not satisfied

### targeted-v5-20261030/insufficient/train/000156

SERVICE DESK NOTE
Merchandise subtotal: $92. Tax: $6. Merchandise discount: $0.
APPLICABLE RULE
Shipping is free if merchandise subtotal minus discount is at least $100. The merchandise discount is between $0 and $60 inclusive. Ignore taxes and delivery fees in this calculation.

Does this order receive free shipping? Use only the supplied facts.

正确答案：The requirement is not satisfied

## insufficient / return:False

### targeted-v5-20261030/insufficient/train/000032

Returns qualify if requested no more than 30 elapsed calendar days after delivery, inclusive. Every order below was delivered between its order date and its return request, inclusive. There are no other requirements.
Case: Order date: 2028-01-03. Return requested: 2028-01-10. Delivered: 2028-01-10.

Does this return qualify? Use only the supplied facts.

正确答案：The requirement is satisfied

### targeted-v5-20261030/insufficient/train/000033

Returns qualify if requested no more than 30 elapsed calendar days after delivery, inclusive. Every order below was delivered between its order date and its return request, inclusive. There are no other requirements.
Case: Order date: 2028-01-03. Return requested: 2028-01-10.

Does this return qualify? Use only the supplied facts.

正确答案：The requirement is satisfied

## insufficient / tenure:False

### targeted-v5-20261030/insufficient/train/000114

{'case': 'Mina transferred to the Support team on 2027-05-14. An unlisted field is not available; do not assume a default value. Company hire date: 2026-07-30.', 'policy': 'The benefit requires at least 365 elapsed days of continuous employment by 2028-05-25. Team transfers do not reset employment. The employee joined the company on or before the stated transfer date and has remained continuously employed through the application date.'}

Is the employee eligible for the benefit? Use only the supplied facts.

正确答案：The requirement is satisfied

### targeted-v5-20261030/insufficient/train/000115

{'case': 'Mina transferred to the Support team on 2027-05-14. An unlisted field is not available; do not assume a default value.', 'policy': 'The benefit requires at least 365 elapsed days of continuous employment by 2028-05-25. Team transfers do not reset employment. The employee joined the company on or before the stated transfer date and has remained continuously employed through the application date.'}

Is the employee eligible for the benefit? Use only the supplied facts.

正确答案：The requirement is satisfied

## insufficient / warranty:False

### targeted-v5-20261030/insufficient/train/000233

This warranty expires on 2028-10-22, inclusive. A claim by that date qualifies only for a manufacturing defect; accidental damage never qualifies. Every claim has exactly one of these causes. Claims after expiry do not qualify regardless of cause.
Case: Claim received: 2028-12-02. Item serial: W10636.

Is the claim covered? Use only the supplied facts.

正确答案：The requirement is not satisfied

### targeted-v5-20261030/insufficient/train/000232

This warranty expires on 2028-10-22, inclusive. A claim by that date qualifies only for a manufacturing defect; accidental damage never qualifies. Every claim has exactly one of these causes. Claims after expiry do not qualify regardless of cause.
Case: Claim received: 2028-12-02. Item serial: W10636. Technician confirmed cause: manufacturing defect.

Is the claim covered? Use only the supplied facts.

正确答案：The requirement is not satisfied

## policy / order

### targeted-v5-20261030/policy/train/000307

CONTRACT SHIPMENT

SCHEDULE AND DATES
Inception: 2028-08-07. B1: purchased; B2: purchased; B3: purchased; B4: purchased. Report each incident within 21 elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.

BENEFIT B4: handling equipment damage
This benefit applies only to the named event handling equipment damage. A claim for a complete handcart and a claim for its caster set both use this benefit. Its limit is $1000.00; deductible $50.00; the part sublimit is $300.00 and applies only when the claimed item is the caster set. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The caster set sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

BENEFIT B3: container water damage
This benefit applies only to the named event container water damage. A claim for a complete container and a claim for its paper label stock both use this benefit. Its limit is $1500.00; deductible $25.00; the part sublimit is $300.00 and applies only when the claimed item is the paper label stock. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The paper label stock sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

BENEFIT B1: parcel impact
This benefit applies only to the named event parcel impact. A claim for a complete parcel and a claim for its glass insert both use this benefit. Its limit is $800.00; deductible $100.00; the part sublimit is $400.00 and applies only when the claimed item is the glass insert. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The glass insert sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

ACCOUNTING AND DOCUMENTS
Eligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.

GENERAL SETTLEMENT RULE
First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero. A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.

BENEFIT B2: refrigeration breakdown
This benefit applies only to the named event refrigeration breakdown. A claim for a complete cooler and a claim for its temperature probe both use this benefit. Its limit is $2000.00; deductible $75.00; the part sublimit is $400.00 and applies only when the claimed item is the temperature probe. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The temperature probe sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

DECISION PRIORITY
Check denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.

OTHER BENEFITS AND ALLOCATION
A complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit's deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.

UNSAFE-STORAGE EXCLUSION AND EXCEPTION
An unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.

INCIDENT FILE
Event: handling equipment damage. Claimed item: handcart. Eligible loss: $1283.00. Incident: 2028-08-21. Reported: 2028-08-30. Usage at incident: 800 hours. Storage: normal. Waiver: none. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.

What payment is due?

正确答案：$950.00

Select the controlling reason under the policy definitions.

正确答案：benefit ceiling

### targeted-v5-20261030/policy/train/000306

CONTRACT SHIPMENT

SCHEDULE AND DATES
Inception: 2028-08-07. B1: purchased; B2: purchased; B3: purchased; B4: purchased. Report each incident within 21 elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.

BENEFIT B4: handling equipment damage
This benefit applies only to the named event handling equipment damage. A claim for a complete handcart and a claim for its caster set both use this benefit. Its limit is $1000.00; deductible $50.00; the part sublimit is $300.00 and applies only when the claimed item is the caster set. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The caster set sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

BENEFIT B3: container water damage
This benefit applies only to the named event container water damage. A claim for a complete container and a claim for its paper label stock both use this benefit. Its limit is $1500.00; deductible $25.00; the part sublimit is $300.00 and applies only when the claimed item is the paper label stock. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The paper label stock sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

BENEFIT B1: parcel impact
This benefit applies only to the named event parcel impact. A claim for a complete parcel and a claim for its glass insert both use this benefit. Its limit is $800.00; deductible $100.00; the part sublimit is $400.00 and applies only when the claimed item is the glass insert. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The glass insert sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

ACCOUNTING AND DOCUMENTS
Eligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.

GENERAL SETTLEMENT RULE
Subtract the deductible from eligible loss first, flooring at zero. Apply the benefit limit and any applicable part sublimit to the remaining loss. A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.

BENEFIT B2: refrigeration breakdown
This benefit applies only to the named event refrigeration breakdown. A claim for a complete cooler and a claim for its temperature probe both use this benefit. Its limit is $2000.00; deductible $75.00; the part sublimit is $400.00 and applies only when the claimed item is the temperature probe. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The temperature probe sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

DECISION PRIORITY
Check denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.

OTHER BENEFITS AND ALLOCATION
A complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit's deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.

UNSAFE-STORAGE EXCLUSION AND EXCEPTION
An unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.

INCIDENT FILE
Event: handling equipment damage. Claimed item: handcart. Eligible loss: $1283.00. Incident: 2028-08-21. Reported: 2028-08-30. Usage at incident: 800 hours. Storage: normal. Waiver: none. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.

What payment is due?

正确答案：$1000.00

Select the controlling reason under the policy definitions.

正确答案：benefit ceiling

## policy / multiple_denial

### targeted-v5-20261030/policy/train/000547

CONTRACT APPLIANCE

OTHER BENEFITS AND ALLOCATION
A complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit's deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.

BENEFIT B3: refrigerator failure
This benefit applies only to the named event refrigerator failure. A claim for a complete refrigerator and a claim for its fan module both use this benefit. Its limit is $2000.00; deductible $100.00; the part sublimit is $500.00 and applies only when the claimed item is the fan module. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The fan module sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

UNSAFE-STORAGE EXCLUSION AND EXCEPTION
An unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.

BENEFIT B1: washer breakdown
This benefit applies only to the named event washer breakdown. A claim for a complete washer and a claim for its valve assembly both use this benefit. Its limit is $1500.00; deductible $50.00; the part sublimit is $200.00 and applies only when the claimed item is the valve assembly. The complete item has no part sublimit. Waiting period: 14 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The valve assembly sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

DECISION PRIORITY
Check denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.

ACCOUNTING AND DOCUMENTS
Eligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.

BENEFIT B4: cleaner impact
This benefit applies only to the named event cleaner impact. A claim for a complete cleaner and a claim for its brush head both use this benefit. Its limit is $1500.00; deductible $25.00; the part sublimit is $500.00 and applies only when the claimed item is the brush head. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The brush head sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

SCHEDULE AND DATES
Inception: 2028-10-03. B1: not purchased; B2: purchased; B3: purchased; B4: purchased. Report each incident within 14 elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.

GENERAL SETTLEMENT RULE
First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero. A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.

BENEFIT B2: oven electrical failure
This benefit applies only to the named event oven electrical failure. A claim for a complete oven and a claim for its thermostat both use this benefit. Its limit is $1500.00; deductible $25.00; the part sublimit is $300.00 and applies only when the claimed item is the thermostat. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The thermostat sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

INCIDENT FILE
Event: washer breakdown. Claimed item: washer. Eligible loss: $1703.00. Incident: 2028-10-20. Reported: 2028-10-20. Usage at incident: 800 hours. Storage: unsafe. Waiver: none. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.

What payment is due?

正确答案：$0.00

Select the controlling reason under the policy definitions.

正确答案：not purchased

### targeted-v5-20261030/policy/train/000546

CONTRACT APPLIANCE

OTHER BENEFITS AND ALLOCATION
A complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit's deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.

BENEFIT B3: refrigerator failure
This benefit applies only to the named event refrigerator failure. A claim for a complete refrigerator and a claim for its fan module both use this benefit. Its limit is $2000.00; deductible $100.00; the part sublimit is $500.00 and applies only when the claimed item is the fan module. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The fan module sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

UNSAFE-STORAGE EXCLUSION AND EXCEPTION
An unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.

BENEFIT B1: washer breakdown
This benefit applies only to the named event washer breakdown. A claim for a complete washer and a claim for its valve assembly both use this benefit. Its limit is $1500.00; deductible $50.00; the part sublimit is $200.00 and applies only when the claimed item is the valve assembly. The complete item has no part sublimit. Waiting period: 14 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The valve assembly sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

DECISION PRIORITY
Check denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.

ACCOUNTING AND DOCUMENTS
Eligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.

BENEFIT B4: cleaner impact
This benefit applies only to the named event cleaner impact. A claim for a complete cleaner and a claim for its brush head both use this benefit. Its limit is $1500.00; deductible $25.00; the part sublimit is $500.00 and applies only when the claimed item is the brush head. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The brush head sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

SCHEDULE AND DATES
Inception: 2028-10-03. B1: purchased; B2: purchased; B3: purchased; B4: purchased. Report each incident within 14 elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.

GENERAL SETTLEMENT RULE
First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero. A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.

BENEFIT B2: oven electrical failure
This benefit applies only to the named event oven electrical failure. A claim for a complete oven and a claim for its thermostat both use this benefit. Its limit is $1500.00; deductible $25.00; the part sublimit is $300.00 and applies only when the claimed item is the thermostat. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The thermostat sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

INCIDENT FILE
Event: washer breakdown. Claimed item: washer. Eligible loss: $1703.00. Incident: 2028-10-20. Reported: 2028-10-20. Usage at incident: 800 hours. Storage: unsafe. Waiver: none. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.

What payment is due?

正确答案：$0.00

Select the controlling reason under the policy definitions.

正确答案：unsafe storage

## policy / boundary

### targeted-v5-20261030/policy/train/000485

CONTRACT APPLIANCE

BENEFIT B4: cleaner impact
This benefit applies only to the named event cleaner impact. A claim for a complete cleaner and a claim for its brush head both use this benefit. Its limit is $1500.00; deductible $75.00; the part sublimit is $300.00 and applies only when the claimed item is the brush head. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The brush head sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

GENERAL SETTLEMENT RULE
First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero. A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.

BENEFIT B1: washer breakdown
This benefit applies only to the named event washer breakdown. A claim for a complete washer and a claim for its valve assembly both use this benefit. Its limit is $1000.00; deductible $75.00; the part sublimit is $200.00 and applies only when the claimed item is the valve assembly. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The valve assembly sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

ACCOUNTING AND DOCUMENTS
Eligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.

BENEFIT B3: refrigerator failure
This benefit applies only to the named event refrigerator failure. A claim for a complete refrigerator and a claim for its fan module both use this benefit. Its limit is $1500.00; deductible $50.00; the part sublimit is $400.00 and applies only when the claimed item is the fan module. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The fan module sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

SCHEDULE AND DATES
Inception: 2028-11-20. B1: purchased; B2: purchased; B3: purchased; B4: purchased. Report each incident within 21 elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.

DECISION PRIORITY
Check denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.

BENEFIT B2: oven electrical failure
This benefit applies only to the named event oven electrical failure. A claim for a complete oven and a claim for its thermostat both use this benefit. Its limit is $2000.00; deductible $75.00; the part sublimit is $300.00 and applies only when the claimed item is the thermostat. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 500 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The thermostat sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

UNSAFE-STORAGE EXCLUSION AND EXCEPTION
An unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.

OTHER BENEFITS AND ALLOCATION
A complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit's deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.

INCIDENT FILE
Event: refrigerator failure. Claimed item: refrigerator. Eligible loss: $1849.00. Incident: 2028-12-20. Reported: 2028-12-29. Usage at incident: 800 hours. Storage: normal. Waiver: none. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.

What payment is due?

正确答案：$1450.00

Select the controlling reason under the policy definitions.

正确答案：benefit ceiling

### targeted-v5-20261030/policy/train/000484

CONTRACT APPLIANCE

BENEFIT B4: cleaner impact
This benefit applies only to the named event cleaner impact. A claim for a complete cleaner and a claim for its brush head both use this benefit. Its limit is $1500.00; deductible $75.00; the part sublimit is $300.00 and applies only when the claimed item is the brush head. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The brush head sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

GENERAL SETTLEMENT RULE
First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero. A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.

BENEFIT B1: washer breakdown
This benefit applies only to the named event washer breakdown. A claim for a complete washer and a claim for its valve assembly both use this benefit. Its limit is $1000.00; deductible $75.00; the part sublimit is $200.00 and applies only when the claimed item is the valve assembly. The complete item has no part sublimit. Waiting period: 0 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 1000 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The valve assembly sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

ACCOUNTING AND DOCUMENTS
Eligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.

BENEFIT B3: refrigerator failure
This benefit applies only to the named event refrigerator failure. A claim for a complete refrigerator and a claim for its fan module both use this benefit. Its limit is $1500.00; deductible $50.00; the part sublimit is $400.00 and applies only when the claimed item is the fan module. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 800 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The fan module sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

SCHEDULE AND DATES
Inception: 2028-11-20. B1: purchased; B2: purchased; B3: purchased; B4: purchased. Report each incident within 21 elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.

DECISION PRIORITY
Check denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.

BENEFIT B2: oven electrical failure
This benefit applies only to the named event oven electrical failure. A claim for a complete oven and a claim for its thermostat both use this benefit. Its limit is $2000.00; deductible $75.00; the part sublimit is $300.00 and applies only when the claimed item is the thermostat. The complete item has no part sublimit. Waiting period: 7 elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above 500 hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.
The thermostat sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.

UNSAFE-STORAGE EXCLUSION AND EXCEPTION
An unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.

OTHER BENEFITS AND ALLOCATION
A complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit's deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.

INCIDENT FILE
Event: refrigerator failure. Claimed item: refrigerator. Eligible loss: $1849.00. Incident: 2028-12-20. Reported: 2028-12-29. Usage at incident: 801 hours. Storage: normal. Waiver: none. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.

What payment is due?

正确答案：$0.00

Select the controlling reason under the policy definitions.

正确答案：usage maximum
