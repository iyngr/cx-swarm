"""
Transcript Retrieval Tool

Fetches call transcripts from BigQuery or Cloud Storage.
"""

import logging
from typing import Optional
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class TranscriptRetrievalTool:
    """Tool for retrieving call transcripts from data storage."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self.bigquery_client = bigquery.Client(project=settings.project_id)
        self.storage_client = storage.Client(project=settings.project_id)
    
    def get_transcript(self, transcript_id: str) -> Optional[str]:
        """
        Retrieve transcript text by ID.
        
        Args:
            transcript_id: The transcript's unique identifier
            
        Returns:
            The full transcript text or None if not found
        """
        try:
            # First try BigQuery
            transcript = self._get_transcript_from_bigquery(transcript_id)
            if transcript:
                return transcript
            
            # Fall back to Cloud Storage
            transcript = self._get_transcript_from_storage(transcript_id)
            if transcript:
                return transcript
            
            logger.warning(f"Transcript {transcript_id} not found in any data source")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving transcript {transcript_id}: {str(e)}")
            return None
    
    def _get_transcript_from_bigquery(self, transcript_id: str) -> Optional[str]:
        """
        Retrieve transcript from BigQuery table.
        
        Args:
            transcript_id: The transcript's unique identifier
            
        Returns:
            The transcript text or None if not found
        """
        try:
            query = f"""
            SELECT transcript_text
            FROM `{self.settings.project_id}.{self.settings.transcript_dataset}.{self.settings.transcript_table}`
            WHERE transcript_id = @transcript_id
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("transcript_id", "STRING", transcript_id)
                ]
            )
            
            logger.info(f"Querying BigQuery for transcript {transcript_id}")
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                transcript_text = row[0]
                logger.info(f"Successfully retrieved transcript {transcript_id} from BigQuery")
                return transcript_text
            
            logger.info(f"Transcript {transcript_id} not found in BigQuery")
            return None
            
        except Exception as e:
            logger.error(f"Error querying BigQuery for transcript {transcript_id}: {str(e)}")
            return None
    
    def _get_transcript_from_storage(self, transcript_id: str) -> Optional[str]:
        """
        Retrieve transcript from Cloud Storage.
        
        Args:
            transcript_id: The transcript's unique identifier
            
        Returns:
            The transcript text or None if not found
        """
        try:
            # Assume transcripts are stored in a bucket with filename pattern
            bucket_name = f"{self.settings.project_id}-transcripts"
            blob_name = f"transcripts/{transcript_id}.txt"
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            if not blob.exists():
                logger.info(f"Transcript {transcript_id} not found in Cloud Storage")
                return None
            
            logger.info(f"Downloading transcript {transcript_id} from Cloud Storage")
            transcript_text = blob.download_as_text()
            
            logger.info(f"Successfully retrieved transcript {transcript_id} from Cloud Storage")
            return transcript_text
            
        except Exception as e:
            logger.error(f"Error retrieving transcript {transcript_id} from Cloud Storage: {str(e)}")
            return None
    
    def store_transcript_analysis(self, transcript_id: str, analysis: dict) -> bool:
        """
        Store analysis results back to BigQuery for future reference.
        
        Args:
            transcript_id: The transcript's unique identifier
            analysis: Dictionary with analysis results
            
        Returns:
            True if successful, False otherwise
        """
        try:
            table_id = f"{self.settings.project_id}.{self.settings.transcript_dataset}.transcript_analysis"
            
            rows_to_insert = [{
                'transcript_id': transcript_id,
                'analysis_timestamp': 'CURRENT_TIMESTAMP()',
                'sentiment_score': analysis.get('sentiment_score'),
                'escalated': analysis.get('escalated', False),
                'resolution_taken': analysis.get('resolution_taken'),
                'agent_notes': analysis.get('agent_notes')
            }]
            
            table = self.bigquery_client.get_table(table_id)
            errors = self.bigquery_client.insert_rows_json(table, rows_to_insert)
            
            if errors:
                logger.error(f"Error inserting analysis for transcript {transcript_id}: {errors}")
                return False
            
            logger.info(f"Successfully stored analysis for transcript {transcript_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing analysis for transcript {transcript_id}: {str(e)}")
            return False