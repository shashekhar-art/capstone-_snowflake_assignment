## Description
<!-- What does this PR do? What problem does it solve? -->

## Type of Change
- [ ] Bronze layer (raw ingestion)
- [ ] Silver layer (transform / cleanse)
- [ ] Gold layer (dimensions / facts)
- [ ] SQL (DDL / queries / views / security)
- [ ] Documentation
- [ ] CI/CD workflow
- [ ] Bug fix
- [ ] Refactor

## Layer(s) Affected
- [ ] BRONZE  — `ADVENTURE_WORKS_DB.BRONZE`
- [ ] SILVER  — `ADVENTURE_WORKS_DB.SILVER`
- [ ] GOLD    — `ADVENTURE_WORKS_DB.GOLD`

## Checklist
- [ ] Code follows project naming conventions (UPPER_SNAKE for SQL objects)
- [ ] All SQL uses `ADVENTURE_WORKS_DB` (not `CAPSTONE_DB`)
- [ ] No hardcoded credentials in code (use env vars / Snowflake Secrets)
- [ ] `profiling.py` or DQ checks pass on affected tables
- [ ] README / data dictionary updated if schema changed
- [ ] CI lint passes locally (`flake8` + `sqlfluff`)

## Testing Done
<!-- How did you verify this works? -->
- [ ] Ran locally against Snowflake dev account
- [ ] Row counts verified pre/post
- [ ] DQ checks (load_facts.py) pass
- [ ] No orphaned FK records in FACT_SALES / FACT_RETURNS

## Snowflake Objects Changed
| Object | Change |
|---|---|
| | |

## Screenshots / Query Output (optional)
<!-- Paste output from profiling.py or analytics_queries.sql if applicable -->
