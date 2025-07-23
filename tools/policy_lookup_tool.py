"""
Policy Lookup Tool

RAG-based tool for searching company policies using Vertex AI Vector Search.
"""

import logging
from typing import Optional, List
from google.cloud import aiplatform
from google.cloud import secretmanager
import vertexai
from vertexai.language_models import TextEmbeddingModel

logger = logging.getLogger(__name__)

class PolicyLookupTool:
    """Tool for searching company policies using vector similarity search."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        
        # Initialize Vertex AI
        vertexai.init(project=settings.project_id, location=settings.vertex_ai_location)
        self.embedding_model = TextEmbeddingModel.from_pretrained(settings.embedding_model)
        
        # Initialize Vector Search client
        self.vector_client = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=settings.vector_search_endpoint_name
        )
    
    def search_policies(self, query: str, top_k: int = 5) -> Optional[str]:
        """
        Search for relevant policies using semantic similarity.
        
        Args:
            query: The search query describing the policy needed
            top_k: Number of top results to return
            
        Returns:
            Combined text of relevant policy documents or None if error
        """
        try:
            logger.info(f"Searching policies for query: {query}")
            
            # Generate embedding for the query
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return None
            
            # Search Vector Index
            search_results = self._search_vector_index(query_embedding, top_k)
            if not search_results:
                return None
            
            # Combine and format results
            policy_text = self._format_search_results(search_results)
            
            logger.info(f"Found {len(search_results)} relevant policy documents")
            return policy_text
            
        except Exception as e:
            logger.error(f"Error searching policies: {str(e)}")
            return None
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for the input text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector or None if error
        """
        try:
            embeddings = self.embedding_model.get_embeddings([text])
            if embeddings and len(embeddings) > 0:
                return embeddings[0].values
            return None
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    def _search_vector_index(self, query_embedding: List[float], top_k: int) -> Optional[List[dict]]:
        """
        Search the vector index for similar documents.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            
        Returns:
            List of search results or None if error
        """
        try:
            # For demonstration purposes, we'll simulate vector search results
            # In a real implementation, this would call the actual Vector Search API
            
            # Simulated policy documents (in a real system these would come from the vector index)
            mock_policies = [
                {
                    "id": "refund_policy_gold",
                    "content": """Refund Policy for Gold Tier Customers:
Gold tier customers are eligible for full refunds within 90 days of purchase.
No restocking fees apply. Expedited processing within 24 hours.
For damaged items, immediate replacement or full refund at customer's choice.""",
                    "score": 0.95
                },
                {
                    "id": "shipping_compensation",
                    "content": """Shipping Issue Compensation Guidelines:
For late deliveries: Offer full shipping refund plus 10% order discount.
For lost packages: Full replacement order with expedited shipping at no charge.
For damaged shipments: Full refund or replacement plus shipping compensation.""",
                    "score": 0.88
                },
                {
                    "id": "appeasement_matrix",
                    "content": """Customer Appeasement Matrix:
High-value customers (LTV > $500): Up to $100 credit without approval.
Order issues: 20-50% discount on next purchase.
Service failures: Expedited shipping upgrade + account credit.""",
                    "score": 0.82
                },
                {
                    "id": "escalation_guidelines",
                    "content": """Escalation Guidelines:
Immediate escalation required for threats to leave or legal action.
Gold/VIP customers: Direct manager contact within 2 hours.
Compensation authority: Front-line agents up to $50, managers up to $200.""",
                    "score": 0.78
                }
            ]
            
            # Return top_k results sorted by score
            results = sorted(mock_policies, key=lambda x: x['score'], reverse=True)[:top_k]
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector index: {str(e)}")
            return None
    
    def _format_search_results(self, search_results: List[dict]) -> str:
        """
        Format search results into readable policy text.
        
        Args:
            search_results: List of search result dictionaries
            
        Returns:
            Formatted policy text
        """
        try:
            formatted_text = "RELEVANT COMPANY POLICIES:\n\n"
            
            for i, result in enumerate(search_results, 1):
                content = result.get('content', '')
                policy_id = result.get('id', f'policy_{i}')
                score = result.get('score', 0)
                
                formatted_text += f"Policy {i} ({policy_id}) - Relevance: {score:.2f}\n"
                formatted_text += f"{content}\n\n"
                formatted_text += "-" * 50 + "\n\n"
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting search results: {str(e)}")
            return "Error formatting policy results"
    
    def add_policy_document(self, document_id: str, content: str, metadata: dict = None) -> bool:
        """
        Add a new policy document to the knowledge base.
        
        Args:
            document_id: Unique identifier for the document
            content: Policy text content
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding for the content
            embedding = self._generate_embedding(content)
            if not embedding:
                return False
            
            # In a real implementation, this would add the document to the vector index
            # For now, we'll log the operation
            logger.info(f"Added policy document {document_id} to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Error adding policy document: {str(e)}")
            return False