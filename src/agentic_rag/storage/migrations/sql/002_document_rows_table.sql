-- ========================================
-- Document Rows Table for CSV/Tabular Data
-- ========================================
-- This table stores individual rows from uploaded CSV/Excel files
-- for SQL querying via the agent's SQL tool

CREATE TABLE IF NOT EXISTS document_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL,
    row_data JSONB NOT NULL,
    row_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key to documents table
    CONSTRAINT fk_dataset
        FOREIGN KEY (dataset_id)
        REFERENCES documents(id)
        ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_document_rows_dataset_id
    ON document_rows(dataset_id);

CREATE INDEX IF NOT EXISTS idx_document_rows_row_data
    ON document_rows USING GIN(row_data);

CREATE INDEX IF NOT EXISTS idx_document_rows_created
    ON document_rows(created_at DESC);

-- Comment for documentation
COMMENT ON TABLE document_rows IS 'Stores individual rows from uploaded CSV/Excel files for SQL querying';
COMMENT ON COLUMN document_rows.dataset_id IS 'References the parent document/dataset in the documents table';
COMMENT ON COLUMN document_rows.row_data IS 'JSON representation of the row data with column names as keys';
COMMENT ON COLUMN document_rows.row_index IS 'Original row number from the source file';
