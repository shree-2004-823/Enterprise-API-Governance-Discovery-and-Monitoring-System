# Application (GUI) Test Report

**Result: 69 / 69 checks passed**  
Run with `python test_app.py` against the real MariaDB database.

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | Anonymous user is redirected to /login | PASS |  |
| 2 | Wrong password rejected | PASS |  |
| 3 | POST without CSRF token is refused (400) | PASS |  |
| 4 | GET / renders (200) | PASS | 200 |
| 5 | GET /apis renders (200) | PASS | 200 |
| 6 | GET /apis/1 renders (200) | PASS | 200 |
| 7 | GET /versions renders (200) | PASS | 200 |
| 8 | GET /endpoints renders (200) | PASS | 200 |
| 9 | GET /subscriptions renders (200) | PASS | 200 |
| 10 | GET /subscriptions/1 renders (200) | PASS | 200 |
| 11 | GET /users renders (200) | PASS | 200 |
| 12 | GET /reports renders (200) | PASS | 200 |
| 13 | GET /concepts renders (200) | PASS | 200 |
| 14 | Consumer cannot open /users | PASS |  |
| 15 | APIs page lists all 4 APIs from api_details_view with api_age() column | PASS |  |
| 16 | Subscriptions page shows subscription_days() duration (365) | PASS |  |
| 17 | Reports page shows view + join + aggregate results | PASS |  |
| 18 | Procedure get_apis_by_owner(1) via GUI endpoint | PASS | ['Notification API', 'User Authentication API'] |
| 19 | Procedure get_api_subscriptions(1) via GUI endpoint | PASS | [['Payment API', 'Sneha Patel', 'v2', 'ACTIVE', '2026-04-10', '2027-04-10'], ['Payment API', 'Kiran Rao', 'v2', 'ACTIVE', '2026-03-01', '2027-03-01']] |
| 20 | API detail page shows procedure result (CALL get_api_subscriptions) | PASS |  |
| 21 | API created through GUI | PASS | 62 |
| 22 | Test versions start ACTIVE | PASS | [['ACTIVE'], ['ACTIVE']] |
| 23 | GUI status change -> TRIGGER after_api_deprecated deprecated the versions | PASS | [['DEPRECATED', 1], ['DEPRECATED', 1]] |
| 24 | GUI shows the trigger message | PASS |  |
| 25 | GUI insert of ACTIVE subscription with past expiry -> stored EXPIRED by trigger | PASS | EXPIRED |
| 26 | Valid future expiry keeps ACTIVE | PASS |  |
| 27 | GUI update to past expiry -> trigger sets EXPIRED and GUI reports it | PASS |  |
| 28 | Expiry sweep button runs (0 overdue ACTIVE rows today) | PASS | ['processed 0 overdue'] |
| 29 | GUI shows MariaDB FK error 1452 for unknown owner | PASS |  |
| 30 | GUI shows MariaDB FK error 1451 deleting an API that has subscriptions | PASS |  |
| 31 | Composite FK rejects version of another API | PASS |  |
| 32 | Consumer is read-only (cannot create API) | PASS |  |
| 33 | Consumer cannot run data-changing demo (403) | PASS |  |
| 34 | Consumer can run read-only demo | PASS |  |
| 35 | Concepts page has section '1. Tables and Relationships' | PASS |  |
| 36 | Concepts page has section '2. DDL Operations' | PASS |  |
| 37 | Concepts page has section '3. DML Operations' | PASS |  |
| 38 | Concepts page has section '4. JOIN Queries' | PASS |  |
| 39 | Concepts page has section '5. Subqueries' | PASS |  |
| 40 | Concepts page has section '6. Aggregate Functions' | PASS |  |
| 41 | Concepts page has section '7. Database Views' | PASS |  |
| 42 | Concepts page has section '8. Triggers' | PASS |  |
| 43 | Concepts page has section '9. Stored Functions' | PASS |  |
| 44 | Concepts page has section '10. Stored Procedures' | PASS |  |
| 45 | Concepts page shows live trigger/function/procedure/view definitions from MariaDB | PASS |  |
| 46 | Concepts demo 'trigger_api' runs (200, no MariaDB errors) | PASS | 200 |
| 47 | Concepts demo 'trigger_sub' runs (200, no MariaDB errors) | PASS | 200 |
| 48 | Concepts demo 'trigger_sweep' runs (200, no MariaDB errors) | PASS | 200 |
| 49 | Concepts demo 'fn_age' runs (200, no MariaDB errors) | PASS | 200 |
| 50 | Concepts demo 'fn_days' runs (200, no MariaDB errors) | PASS | 200 |
| 51 | Concepts demo 'fn_label' runs (200, no MariaDB errors) | PASS | 200 |
| 52 | Concepts demo 'ddl' runs (200, no MariaDB errors) | PASS | 200 |
| 53 | Concepts demo 'dml' runs (200, no MariaDB errors) | PASS | 200 |
| 54 | Concepts demo 'fk_demo' runs (200, no MariaDB errors) | PASS | 200 |
| 55 | Concepts demo 'show_create' runs (200, no MariaDB errors) | PASS | 200 |
| 56 | Concepts demo 'view_api_details' runs (200, no MariaDB errors) | PASS | 200 |
| 57 | Concepts demo 'view_api_version' runs (200, no MariaDB errors) | PASS | 200 |
| 58 | Concepts demo 'having' runs (200, no MariaDB errors) | PASS | 200 |
| 59 | Concepts demo 'sub_derived' runs (200, no MariaDB errors) | PASS | 200 |
| 60 | Time-travel sweep AFTER shows subscriptions 1-3 EXPIRED | PASS | [[1, 'EXPIRED', '2027-03-01'], [2, 'EXPIRED', '2027-03-01'], [3, 'EXPIRED', '2027-03-05'], [4, 'ACTIVE', '2027-04-10'], [5, 'ACTIVE', '2027-04-15'], [99, 'EXPIR |
| 61 | api_age('2020-06-15') through GUI = 6 (CURDATE 2026-11-17) | PASS | [6, '2026-11-18'] |
| 62 | Unknown demo key / raw SQL is refused | PASS |  |
| 63 | SQL injection in procedure parameter refused | PASS |  |
| 64 | SQL injection in table name refused | PASS |  |
| 65 | SQL injection via function date refused | PASS |  |
| 66 | Run endpoint needs CSRF header | PASS |  |
| 67 | API table still exists after injection attempts | PASS |  |
| 68 | Clean-up via GUI: test subscription and API removed | PASS |  |
| 69 | Clean-up: cascade removed the test versions | PASS |  |