-- NEW TABLE: COMPLAINT_EMBEDDINGS
-- Corrected: One embedding per complaint using sentence-transformers/all-MiniLM-L6-v2
-- Dimension: 384 (fixed)

CREATE TABLE IF NOT EXISTS complaint_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    -- pgvector extension needed for vector column
    -- Install: CREATE EXTENSION IF NOT EXISTS vector;
    -- Vector dimension: 384 for all-MiniLM-L6-v2
    embedding_vector vector(384),
    embedding_model VARCHAR(100) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW index for fast similarity search (requires pgvector)
-- This allows fast vector similarity queries using <-> operator
CREATE INDEX idx_complaint_embeddings_vector ON complaint_embeddings 
USING hnsw (embedding_vector vector_cosine_ops);

CREATE INDEX idx_complaint_embeddings_complaint_id ON complaint_embeddings(complaint_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_complaint_embeddings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER complaint_embeddings_updated_at_trigger
BEFORE UPDATE ON complaint_embeddings
FOR EACH ROW
EXECUTE FUNCTION update_complaint_embeddings_timestamp();

-- NEW TABLE: KNOWLEDGE_DOCUMENT_CHUNKS
-- Critical addition from misleads chat - RAG needs a document base
-- Stores knowledge base documents split into chunks for RAG retrieval

CREATE TABLE IF NOT EXISTS knowledge_document_chunks (
    chunk_id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(department_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER, -- Order of chunk within document
    chunk_embedding vector(384),
    embedding_model VARCHAR(100) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    metadata JSONB, -- Store additional metadata like source, tags, etc.
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for fast lookup
CREATE INDEX idx_knowledge_chunks_department_id ON knowledge_document_chunks(department_id);
CREATE INDEX idx_knowledge_chunks_document_id ON knowledge_document_chunks(document_id);
CREATE INDEX idx_knowledge_chunks_active ON knowledge_document_chunks(is_active);

-- Create vector index for similarity search
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_document_chunks 
USING hnsw (chunk_embedding vector_cosine_ops);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_knowledge_chunks_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER knowledge_chunks_updated_at_trigger
BEFORE UPDATE ON knowledge_document_chunks
FOR EACH ROW
EXECUTE FUNCTION update_knowledge_chunks_timestamp();
