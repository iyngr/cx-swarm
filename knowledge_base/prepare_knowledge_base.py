"""
Knowledge Base Preparation Script

This script prepares company policy documents for the RAG system by:
1. Processing documents into chunks
2. Generating embeddings
3. Ingesting into Vertex AI Vector Search
"""

import os
import json
import logging
from typing import List, Dict, Any
from google.cloud import aiplatform
import vertexai
from vertexai.language_models import TextEmbeddingModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeBaseBuilder:
    """Builder for the company policy knowledge base."""
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
    def process_policy_documents(self, documents_dir: str) -> List[Dict[str, Any]]:
        """
        Process policy documents into chunks suitable for vector search.
        
        Args:
            documents_dir: Directory containing policy documents
            
        Returns:
            List of document chunks with metadata
        """
        chunks = []
        
        # Sample policy documents (in production, these would be loaded from files)
        sample_policies = [
            {
                "filename": "refund_policy.txt",
                "content": """
                REFUND POLICY
                
                Standard Customers:
                - 30-day return window for unopened items
                - 15% restocking fee applies
                - Customer pays return shipping
                
                Gold Tier Customers:
                - 90-day return window
                - No restocking fees
                - Free return shipping
                - Expedited refund processing (24-48 hours)
                
                VIP/Premium Customers:
                - 120-day return window
                - No restocking fees
                - Free return shipping
                - Same-day refund processing
                - White-glove return service available
                """
            },
            {
                "filename": "shipping_compensation.txt", 
                "content": """
                SHIPPING ISSUE COMPENSATION GUIDELINES
                
                Late Delivery (1-3 days):
                - Full shipping refund
                - 10% discount on next order
                
                Late Delivery (4+ days):
                - Full shipping refund
                - 20% discount on next order
                - Optional expedited shipping on replacement
                
                Lost Packages:
                - Immediate replacement order
                - Expedited shipping at no charge
                - Additional 15% discount for inconvenience
                
                Damaged Shipments:
                - Customer choice: full refund or replacement
                - Expedited replacement shipping
                - Compensation for any time-sensitive issues
                """
            },
            {
                "filename": "appeasement_matrix.txt",
                "content": """
                CUSTOMER APPEASEMENT AUTHORITY MATRIX
                
                Front-line Agents:
                - Up to $50 credit without approval
                - Free shipping upgrades
                - Standard discount coupons (up to 20%)
                
                Supervisors:
                - Up to $150 credit without approval
                - Expedited processing
                - Premium discount coupons (up to 40%)
                
                Managers:
                - Up to $500 credit
                - Full order replacements
                - Custom compensation packages
                
                High-Value Customer Escalation:
                - LTV > $500: Automatic supervisor involvement
                - LTV > $2000: Automatic manager involvement
                - VIP tier: Direct executive support contact
                """
            },
            {
                "filename": "escalation_procedures.txt",
                "content": """
                ESCALATION PROCEDURES
                
                Immediate Escalation Required:
                - Threats of legal action
                - Social media complaints with high visibility
                - Customer threatens to leave/cancel all services
                - Health or safety concerns
                
                Gold/VIP Customer Escalation:
                - All complaints escalate to supervisor within 2 hours
                - Manager contact required within 4 hours
                - Executive notification for unresolved issues after 24 hours
                
                Response Time Requirements:
                - Standard customers: 24 hours
                - Gold customers: 4 hours
                - VIP customers: 1 hour
                - Emergency issues: 15 minutes
                """
            },
            {
                "filename": "product_issue_guidelines.txt",
                "content": """
                PRODUCT ISSUE RESOLUTION GUIDELINES
                
                Defective Products:
                - Immediate replacement for items under warranty
                - Full refund option if customer prefers
                - Expedited shipping for replacements
                
                Quality Issues:
                - Photo documentation required
                - Quality team review for recurring issues
                - Compensation based on issue severity
                
                Missing Items:
                - Ship missing items immediately
                - Upgrade shipping to expedited
                - Provide tracking information promptly
                
                Wrong Items Shipped:
                - Keep incorrect items (if value < $25)
                - Expedited shipping for correct items
                - Return label for high-value incorrect items
                """
            }
        ]
        
        for policy in sample_policies:
            # Split content into semantic chunks
            policy_chunks = self._chunk_document(policy["content"], policy["filename"])
            chunks.extend(policy_chunks)
        
        logger.info(f"Processed {len(chunks)} policy chunks")
        return chunks
    
    def _chunk_document(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """
        Split a document into semantic chunks.
        
        Args:
            content: Document content
            filename: Source filename
            
        Returns:
            List of document chunks
        """
        # Simple chunking strategy: split by paragraphs/sections
        sections = content.strip().split('\n\n')
        chunks = []
        
        for i, section in enumerate(sections):
            section = section.strip()
            if len(section) > 50:  # Filter out very short sections
                chunk = {
                    "id": f"{filename}_{i}",
                    "content": section,
                    "source": filename,
                    "chunk_index": i,
                    "metadata": {
                        "document_type": "policy",
                        "source_file": filename
                    }
                }
                chunks.append(chunk)
        
        return chunks
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Chunks with embeddings added
        """
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        # Extract text content for embedding
        texts = [chunk["content"] for chunk in chunks]
        
        # Generate embeddings in batches
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_chunks = chunks[i:i + batch_size]
            
            try:
                embeddings = self.embedding_model.get_embeddings(batch_texts)
                
                for j, embedding in enumerate(embeddings):
                    batch_chunks[j]["embedding"] = embedding.values
                    
                logger.info(f"Generated embeddings for batch {i//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//batch_size + 1}: {str(e)}")
        
        return chunks
    
    def save_knowledge_base(self, chunks: List[Dict[str, Any]], output_file: str):
        """
        Save the knowledge base to a file.
        
        Args:
            chunks: Document chunks with embeddings
            output_file: Output file path
        """
        knowledge_base = {
            "metadata": {
                "total_chunks": len(chunks),
                "embedding_model": "text-embedding-004",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "chunks": chunks
        }
        
        with open(output_file, 'w') as f:
            json.dump(knowledge_base, f, indent=2)
        
        logger.info(f"Saved knowledge base to {output_file}")
    
    def create_vector_search_index(self, index_display_name: str, 
                                 knowledge_base_file: str) -> str:
        """
        Create a Vertex AI Vector Search index from the knowledge base.
        
        Args:
            index_display_name: Display name for the index
            knowledge_base_file: Path to knowledge base JSON file
            
        Returns:
            Index resource name
        """
        # This is a simplified example - in production you would use the
        # Vertex AI Vector Search API to create and populate the index
        logger.info(f"Creating Vector Search index: {index_display_name}")
        
        # For demonstration, we'll just log the process
        logger.info("Vector Search index creation would happen here")
        logger.info(f"Index would be populated from {knowledge_base_file}")
        
        return f"projects/{self.project_id}/locations/{self.location}/indexes/policy-knowledge-base"

def main():
    """Main function to build the knowledge base."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-project-id')
    
    builder = KnowledgeBaseBuilder(project_id)
    
    # Process policy documents
    chunks = builder.process_policy_documents("./knowledge_base/policies")
    
    # Generate embeddings
    chunks_with_embeddings = builder.generate_embeddings(chunks)
    
    # Save knowledge base
    os.makedirs("./knowledge_base", exist_ok=True)
    builder.save_knowledge_base(chunks_with_embeddings, "./knowledge_base/policy_knowledge_base.json")
    
    # Create Vector Search index
    index_name = builder.create_vector_search_index("Policy Knowledge Base", 
                                                   "./knowledge_base/policy_knowledge_base.json")
    
    logger.info(f"Knowledge base preparation complete. Index: {index_name}")

if __name__ == "__main__":
    main()