# Database ER Diagram

This diagram follows the DDL in `sql/api_management_refined.sql`. It includes all eight base tables, their declared attributes, primary keys, unique keys, foreign keys, and the subscription-to-version composite relationship.

```mermaid
erDiagram
    ROLE {
        INT role_id PK
        VARCHAR role_name UK
        VARCHAR description
    }

    TEAM {
        INT team_id PK
        VARCHAR team_name UK
        VARCHAR description
    }

    USER {
        INT user_id PK
        VARCHAR full_name
        VARCHAR email UK
        VARCHAR phone
        VARCHAR password_hash
        INT role_id FK
        INT team_id FK
        VARCHAR status
        TIMESTAMP created_at
    }

    API {
        INT api_id PK
        VARCHAR api_name UK
        TEXT description
        VARCHAR category
        VARCHAR status
        INT owner_id FK
        TIMESTAMP created_at
    }

    API_VERSION {
        INT version_id PK
        INT api_id FK
        VARCHAR version_number
        DATE release_date
        VARCHAR status
        TEXT changelog
        DATE deprecated_date
        INT version_id_api_id UK
    }

    ENDPOINT {
        INT endpoint_id PK
        INT version_id FK
        VARCHAR method
        VARCHAR endpoint_path
        TEXT description
    }

    SUBSCRIPTION {
        INT subscription_id PK
        INT api_id FK
        INT version_id FK
        INT consumer_id FK
        VARCHAR status
        DATE subscribe_date
        DATE expires_at
    }

    PERMISSION {
        INT permission_id PK
        INT subscription_id FK
        VARCHAR permission_type
        BOOLEAN allowed
        TIMESTAMP created_at
    }

    ROLE ||--o{ USER : "fk_user_role"
    TEAM ||--o{ USER : "fk_user_team"
    USER ||--o{ API : "fk_api_owner"
    API ||--o{ API_VERSION : "fk_version_api"
    API_VERSION ||--o{ ENDPOINT : "fk_endpoint_version"
    API ||--o{ SUBSCRIPTION : "fk_subscription_api"
    USER ||--o{ SUBSCRIPTION : "fk_subscription_consumer"
    SUBSCRIPTION ||--o{ PERMISSION : "fk_permission_subscription"

    API_VERSION ||--o{ SUBSCRIPTION : "fk_subscription_version_api: (version_id, api_id)"
```

## Relationship and key notes

- Each `USER` must refer to exactly one `ROLE` and one `TEAM`; a role or team may have zero or many users.
- Each `API` has one owner (`USER`). An owner may own zero or many APIs.
- Each `API_VERSION` belongs to one `API`; an API may have zero or many versions.
- Each `ENDPOINT` belongs to one version; a version may have zero or many endpoints.
- A `SUBSCRIPTION` refers to one API, one version, and one consumer user. Each of those parent records can be referenced by zero or many subscriptions.
- `fk_subscription_version_api` is composite: `(SUBSCRIPTION.version_id, SUBSCRIPTION.api_id)` references `(API_VERSION.version_id, API_VERSION.api_id)`. This prevents a subscription from combining an API with another API's version. `API_VERSION` declares a unique key on `(version_id, api_id)` to support this relationship.
- A subscription may have zero or many `PERMISSION` rows. The pair `(subscription_id, permission_type)` is unique, so a permission type can occur at most once per subscription.
- `UK` means a declared unique key. The ER notation's `version_id_api_id` label represents the unique pair `(version_id, api_id)`, not a separate stored column.
- The diagram shows declared foreign-key relationships only. Views, triggers, functions, and procedures are database objects, not entities in this ER model.
