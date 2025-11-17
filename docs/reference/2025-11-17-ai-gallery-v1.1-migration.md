# AI Gallery v1.1 Migration Notes

These SQL statements migrate an existing v1.0 database to the v1.1 schema (videos, thumbnails, decimal ratings). Run them within a transaction after stopping the application.

```sql
-- 1. Media type for each asset (default to images).
ALTER TABLE image ADD COLUMN media_type TEXT NOT NULL DEFAULT 'image';
UPDATE image SET media_type = 'image' WHERE media_type IS NULL;

-- 2. Optional thumbnail pointer for overrides and required video stills.
ALTER TABLE image ADD COLUMN thumbnail_file TEXT;

-- 3. Convert integer ratings to REAL (tenths). SQLite requires a table rewrite.
ALTER TABLE image RENAME TO image_old;
CREATE TABLE image (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    prompt_meta JSON,
    ai_model TEXT,
    notes TEXT,
    rating REAL,
    thumbnail_file TEXT,
    captured_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
INSERT INTO image (
    id, file_name, media_type, prompt_text, prompt_meta, ai_model, notes,
    rating, thumbnail_file, captured_at, created_at, updated_at
)
SELECT
    id,
    file_name,
    media_type,
    prompt_text,
    prompt_meta,
    ai_model,
    notes,
    CASE WHEN rating IS NULL THEN NULL ELSE ROUND(CAST(rating AS REAL), 1) END,
    thumbnail_file,
    captured_at,
    created_at,
    updated_at
FROM image_old;
DROP TABLE image_old;
```

Back up `app.db` before running the migration. After applying the SQL above, restart the FastAPI service so SQLModel reloads the updated schema.
