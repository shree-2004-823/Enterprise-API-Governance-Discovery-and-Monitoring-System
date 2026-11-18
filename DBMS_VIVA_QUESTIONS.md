# DBMS Viva Questions and Answers

## Project architecture

1. **What is the purpose of this project?**  
   It manages API governance records—APIs, versions, endpoints, subscriptions, permissions, and users—and demonstrates DBMS concepts through a Flask interface backed by MariaDB.

2. **What are the main layers of the application?**  
   The browser uses HTML, CSS, and JavaScript; Flask handles routes and rendering; PyMySQL connects Flask to MariaDB; database objects enforce and implement SQL behavior.

3. **What does `app.py` do?**  
   It defines the web routes, login flow, role checks, form processing, and calls to the database layer and DBMS demo engine.

4. **What is the responsibility of `db.py`?**  
   It opens and closes database connections and provides helpers for queries, writes, result normalization, and stored-procedure calls.

5. **Where does the database logic live?**  
   Schema objects are defined in `sql/api_management_refined.sql`. MariaDB executes its constraints, views, triggers, functions, and procedures; Flask sends SQL and displays the returned results.

## Flask backend and connectivity

6. **How does Flask communicate with MariaDB?**  
   Through PyMySQL, using the connection settings in `config.py`. SQL parameters are passed separately from query strings for parameterized statements.

7. **What is a Flask route?**  
   A route maps an HTTP path and method to a Python view function. For example, `/apis` displays API records and `/apis/add` handles an API creation POST.

8. **How are database records displayed?**  
   The route queries MariaDB, passes the returned data to a Jinja template, and Flask renders HTML for the browser.

9. **Why does `db.call_proc` consume all result sets?**  
   A procedure call can return multiple result sets and a trailing status packet. Consuming these sets prevents the PyMySQL connection from remaining out of sync.

10. **Where are the database host and port configured?**  
    In `config.py`, with environment-variable overrides such as `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.

11. **Does this project use MySQL or MariaDB?**  
    The SQL is MySQL-family SQL, but the README documents running it with XAMPP MariaDB. The checked-in database verification report is specifically a MariaDB report; MySQL 8 compatibility should be independently tested.

12. **What does `setup_db.py` do?**  
    It parses the SQL file's `DELIMITER` blocks for PyMySQL, creates the schema from the SQL, skips demonstration `SELECT`/`CALL` statements, and replaces seed placeholder password hashes.

## Relational design and normalization

13. **What is a relational database?**  
    It stores data in tables whose rows represent records and whose columns represent attributes. Keys relate records across tables.

14. **What does normalization achieve?**  
    It structures data to reduce unnecessary duplication and update anomalies. This project separates roles, teams, users, APIs, versions, endpoints, subscriptions, and permissions into related tables.

15. **Why is `ROLE` separate from `USER`?**  
    Multiple users can share one role; each user stores a `role_id` rather than repeating the role description in every user row.

16. **Why is `API_VERSION` separate from `API`?**  
    One API can have multiple releases, each with its own version number, release date, status, changelog, and deprecation date.

17. **What is a primary key?**  
    A primary key uniquely identifies each row and cannot be null. Examples include `API.api_id` and `SUBSCRIPTION.subscription_id`.

18. **What is a foreign key?**  
    A foreign key requires a child-row value to correspond to a referenced parent key, enforcing referential integrity. For example, `API.owner_id` references `USER.user_id`.

19. **What is a unique constraint? Give project examples.**  
    It prevents duplicate values in a column or column combination. The schema requires unique role names, team names, user emails, API names, API/version-number pairs, endpoint method/path per version, and permission types per subscription.

20. **What is a composite key or composite foreign key?**  
    It uses more than one column as a key. `SUBSCRIPTION(version_id, api_id)` references `API_VERSION(version_id, api_id)` so a subscription cannot pair an API with a version belonging to a different API.

21. **What is the difference between `CASCADE` and `RESTRICT`?**  
    `CASCADE` propagates a parent delete/update to related child rows; `RESTRICT` rejects an operation when dependent rows exist. This schema cascades API deletion to versions, versions to endpoints, and subscriptions to permissions, while restricting deletion of referenced owners/APIs.

22. **What does `NOT NULL` mean?**  
    The column must have a value. For example, each API must have a name and owner, and each subscription must have API, version, consumer, and subscription date values.

23. **What is an index, and why is it used?**  
    An index helps the database find rows efficiently, often at the cost of extra storage and write work. The schema indexes foreign-key and commonly filtered columns such as API status and subscription status/expiry.

## SQL queries and database objects

24. **What does an `INNER JOIN` do?**  
    It returns rows with matching join keys in both tables. The API-owner report joins `API.owner_id` to `USER.user_id`.

25. **What does a `LEFT JOIN` do?**  
    It keeps all rows from the left table and includes matching right-side data when available. The versions-per-API query can therefore show an API with zero versions.

26. **Why does the subscription detail query join several tables?**  
    Subscription data stores IDs; joins to `USER`, `API`, and `API_VERSION` display the consumer name, API name, and version number with each subscription.

27. **What is `GROUP BY` used for?**  
    It groups rows so aggregate calculations can be made per group. The project groups subscriptions by API to count subscriptions per API.

28. **How is `HAVING` different from `WHERE`?**  
    `WHERE` filters individual rows before grouping; `HAVING` filters groups after aggregate values are calculated. The project uses `HAVING COUNT(...) > 1` for APIs with multiple subscriptions.

29. **What is a subquery?**  
    A query nested inside another query. The project uses an `IN` subquery to find APIs with subscriptions and a scalar subquery to find each API's latest release.

30. **What is a correlated subquery?**  
    A nested query that refers to a value from the outer query. The `NOT EXISTS` example checks whether a subscription exists for the API currently being examined.

31. **What are aggregate functions?**  
    Functions that summarize sets of rows. The reports demonstrate `COUNT`, `SUM`, `AVG`, `MIN`, and `MAX`.

32. **What is a view?**  
    A named stored `SELECT` that can be queried like a virtual table. It normally stores the query definition rather than a separate copy of the selected rows.

33. **What do the three project views show?**  
    `api_details_view` combines APIs and owners; `api_version_view` combines API and version data; `subscription_details_view` combines subscriptions with consumer, API, and version information.

## Triggers, functions, and procedures

34. **What is a trigger?**  
    A database program that runs automatically when a configured table event occurs. These triggers are tied to inserts or updates, not to the passage of time alone.

35. **What does `after_api_deprecated` do?**  
    After an API changes to `DEPRECATED`, it marks that API's currently active versions deprecated and fills a missing deprecated date.

36. **What does `check_subscription_expiry` do?**  
    Before a subscription update, it sets the new status to `EXPIRED` if the non-null `expires_at` value is earlier than MariaDB's `CURDATE()`.

37. **Why is there an insert expiry trigger as well as an update expiry trigger?**  
    A new subscription can already have a past expiry date. `check_subscription_expiry_insert` applies the rule when the row is first inserted; the update trigger handles later changes.

38. **Why does the expiry sweep update rows if the date already passed?**  
    A trigger doesn't run just because time passes. The application touches overdue active rows with an update so MariaDB invokes the before-update trigger to set their status.

39. **What is a stored function?**  
    A database routine that returns a value and can be used in expressions, often in `SELECT`. This project defines three functions.

40. **What does `api_age` calculate?**  
    It returns whole years from the supplied date to `CURDATE()` using `TIMESTAMPDIFF(YEAR, ...)`. A null input returns null.

41. **What does `subscription_days` calculate?**  
    It returns the day difference from `start_date` to `end_date` using `DATEDIFF(end_date, start_date)`. A null argument results in null.

42. **What does `api_status_label` return?**  
    It maps `ACTIVE`, `DEPRECATED`, `MAINTENANCE`, and `INACTIVE` to descriptive text and returns “Unknown API status” for other inputs.

43. **What is a stored procedure?**  
    A named database routine invoked with `CALL`; it can execute SQL and return result sets. It is useful for reusable database operations.

44. **What does `get_apis_by_owner` return?**  
    It accepts an owner ID and returns that user's APIs, ordered by API name.

45. **What does `get_api_subscriptions` return?**  
    It accepts an API ID and returns subscription details joined with consumer, API, and version information, newest first.

## Transactions, CRUD, and testing

46. **What is a transaction?**  
    A group of database statements treated as a unit. It can be committed to preserve changes or rolled back to undo them.

47. **How do the concept demos avoid lasting test changes?**  
    Data-changing demos use transactions that are rolled back or create/drop a disposable object. The DML demo also deletes its temporary team.

48. **What does CRUD stand for?**  
    Create, Read, Update, and Delete. For example, the API routes insert, list/detail-select, edit/status-update, and delete API records.

49. **Why use parameterized SQL?**  
    It keeps values separate from SQL syntax, which helps prevent values from being interpreted as executable SQL. The app's database calls generally pass query arguments separately.

50. **What is the purpose of a foreign-key test?**  
    It verifies that the database rejects invalid references. For example, inserting an API with a nonexistent owner should fail.

51. **What does the database test suite cover?**  
    The included `test_database.py` checks declared objects, constraints, triggers, functions, procedures, views, and query results against MariaDB.

52. **What does the GUI test suite cover?**  
    The included `test_app.py` exercises Flask pages, authentication and role behavior, database actions through routes, and controlled concepts demos.

53. **Why should these tests run against a test database?**  
    They interact with real database records and some GUI checks perform writes before cleaning them up. An isolated database protects real or important data from accidental test changes.
