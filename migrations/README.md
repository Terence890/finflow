"""
Alembic Migrations for PinkLedger.

This directory contains database schema migrations managed by Alembic.

## Usage

### Initialize migrations (one-time):
```bash
alembic init migrations
```

### Create new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations:
```bash
alembic upgrade head
```

### Rollback migration:
```bash
alembic downgrade -1
```

### Check migration status:
```bash
alembic current
```

## Naming Convention

Migrations follow the pattern: `NNN_description_of_change.py`

- `001_initial_schema.py` - Initial database tables
- `002_add_user_roles.py` - Add admin roles
- `003_add_audit_table.py` - Add audit logging

## See Also

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
"""
