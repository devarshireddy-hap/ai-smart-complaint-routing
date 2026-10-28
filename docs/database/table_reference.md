# CampusCare database table reference

The canonical PostgreSQL schema is [00_init.sql](../../database/schema/00_init.sql). `PK` means primary key; `FK` means foreign key. Columns without a key marker are ordinary data columns. The schema contains 15 application tables.

## Accounts and access

### `users`

| Column | Key / relationship |
|---|---|
| `user_id` | PK |
| `email`, `name`, `password_hash`, `phone`, `user_type` | Account identity and sign-in data |
| `department_id` | FK -> `departments.department_id` |
| `is_active`, `created_at`, `updated_at`, `last_login`, `google_id`, `profile_picture_url` | Account state and profile |

`user_type` is an account type (`STUDENT`, `FACULTY`, or `WORKING_STAFF`). The authorization role is stored separately through `user_roles`.

### `roles`

| Column | Key / relationship |
|---|---|
| `role_id` | PK |
| `role_name` | Unique role name: `USER`, `OFFICER`, or `ADMIN` |
| `description`, `created_at` | Role metadata |

### `permissions`

| Column | Key / relationship |
|---|---|
| `permission_id` | PK |
| `permission_name` | Unique permission name |
| `description`, `module`, `created_at` | Permission metadata |

### `user_roles`

| Column | Key / relationship |
|---|---|
| (`user_id`, `role_id`) | Composite PK |
| `user_id` | FK -> `users.user_id` |
| `role_id` | FK -> `roles.role_id` |
| `assigned_at`, `assigned_by` | Assignment metadata; `assigned_by` is FK -> `users.user_id` |

### `role_permissions`

| Column | Key / relationship |
|---|---|
| (`role_id`, `permission_id`) | Composite PK |
| `role_id` | FK -> `roles.role_id` |
| `permission_id` | FK -> `permissions.permission_id` |
| `assigned_at` | Assignment timestamp |

## Departments and complaints

### `departments`

| Column | Key / relationship |
|---|---|
| `department_id` | PK |
| `department_name` | Unique department name |
| `head_id` | FK -> `users.user_id` |
| `description`, `email`, `phone`, `is_active`, `created_at`, `updated_at` | Department metadata |

### `categories`

| Column | Key / relationship |
|---|---|
| `category_id` | PK |
| `department_id` | FK -> `departments.department_id` |
| `category_name`, `description`, `sla_hours`, `is_active`, `created_at`, `updated_at` | Category data |
| (`category_name`, `department_id`) | Unique together |

### `complaints`

| Column | Key / relationship |
|---|---|
| `complaint_id` | PK |
| `user_id` | FK -> `users.user_id` (reporter) |
| `category_id` | FK -> `categories.category_id` |
| `department_id`, `ai_suggested_department_id` | Each FK -> `departments.department_id` |
| `duplicate_of` | Self-referencing FK -> `complaints.complaint_id` |
| `title`, `description`, `priority`, `status`, `urgency_score`, `location`, `attachment_urls`, `submission_mode`, `is_duplicate` | Complaint details and workflow |
| `confidence_score`, `ai_suggested_priority`, `rag_relevant_docs` | AI suggestion metadata |
| `created_at`, `updated_at`, `resolved_at` | Timestamps |

### `complaint_history`

| Column | Key / relationship |
|---|---|
| `history_id` | PK; the activity ID shown in the complaint timeline |
| `complaint_id` | FK -> `complaints.complaint_id` |
| `changed_by` | FK -> `users.user_id` |
| `change_type`, `old_values`, `new_values`, `changed_field`, `change_description`, `changed_at`, `ip_address` | Activity details and before/after state |

### `complaint_embeddings`

| Column | Key / relationship |
|---|---|
| `embedding_id` | PK |
| `complaint_id` | Unique FK -> `complaints.complaint_id` |
| `embedding_vector`, `embedding_model`, `created_at`, `updated_at` | Vector search data |

### `knowledge_document_chunks`

| Column | Key / relationship |
|---|---|
| `chunk_id` | PK |
| `department_id` | FK -> `departments.department_id` |
| `document_id`, `chunk_index` | Source document identifier and chunk order; unique together |
| `title`, `chunk_text`, `chunk_embedding`, `embedding_model`, `metadata`, `is_active`, `created_at`, `updated_at` | Knowledge content and vector search data |

## Administration and feedback

### `audit_logs`

| Column | Key / relationship |
|---|---|
| `log_id` | PK; the activity ID shown in System activity |
| `user_id` | FK -> `users.user_id` (actor) |
| `action`, `resource_type`, `resource_id`, `old_values`, `new_values`, `status`, `ip_address`, `user_agent`, `created_at` | Audit details; `resource_id` identifies the affected application record |

### `backup_records`

| Column | Key / relationship |
|---|---|
| `backup_id` | PK |
| `created_by` | FK -> `users.user_id` |
| `backup_name` | Unique backup name |
| `backup_type`, `backup_location`, `size_mb`, `status`, `created_at`, `expires_at` | Backup metadata |

### `rollback_records`

| Column | Key / relationship |
|---|---|
| `rollback_id` | PK |
| `backup_id` | FK -> `backup_records.backup_id` |
| `initiated_by` | FK -> `users.user_id` |
| `reversed_history_id` | FK -> `complaint_history.history_id`; activity that was undone |
| `rollback_history_id` | FK -> `complaint_history.history_id`; new activity recording the rollback |
| `status`, `reason`, `created_at`, `completed_at` | Rollback metadata |

### `feedback`

| Column | Key / relationship |
|---|---|
| `feedback_id` | PK |
| `complaint_id` | FK -> `complaints.complaint_id` |
| `user_id` | FK -> `users.user_id` |
| `rating`, `comment`, `is_helpful`, `created_at` | Reporter feedback |

## Inspecting a local database

From PowerShell in the project directory:

```powershell
docker compose exec postgres psql -U postgres -d complaint_routing
```

At the `psql` prompt, `\dt` lists tables and `\d+ complaints` displays a table's columns, constraints, and indexes. For example, inspect the rollback activity references with `\d+ rollback_records`. Use `SELECT` to read rows; avoid publishing personal account or complaint data.
