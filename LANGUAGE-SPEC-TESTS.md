# RuleForge Conformance Tests

## Valid Examples (Must Accept)
VALID-001:
RULE active_customer
LANGUAGE 1
WHEN customer.active == true
THEN ALLOW
END

VALID-002:
RULE premium_customer
LANGUAGE 1
WHEN customer.age >= 65 AND customer.email IS NOT NULL
THEN APPLY "senior_discount" ALERT "Welcome premium customer"
END

VALID-003:
RULE invoice_total_check
LANGUAGE 1
WHEN (invoice.amount * 1.21) > 50000 OR customer.tax_exempt == true
THEN ALLOW
END

## Invalid Examples (Must Reject)
INVALID-001:
RULE invalid_type_mismatch
LANGUAGE 1
WHEN customer.age > "65"
THEN ALLOW
END
Expected: RF3001 Type Error

INVALID-002:
RULE invalid_nested_prop
LANGUAGE 1
WHEN customer.address.city == "Gesell"
THEN ALLOW
END
Expected: RF2001 Parse Error

INVALID-003:
RULE invalid_missing_end
LANGUAGE 1
WHEN customer.age >= 18
THEN ALLOW
Expected: RF2001 Parse Error

INVALID-004:
RULE invalid_random_func
LANGUAGE 1
WHEN now() > customer.start_date
THEN ALLOW
END
Expected: RF3003 Semantic Error
