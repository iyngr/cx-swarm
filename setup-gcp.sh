#!/bin/bash

# Google Cloud setup script for Customer Experience Rescue Swarm
# This script sets up the required Google Cloud resources

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}

echo "Setting up Customer Experience Rescue Swarm for project: $PROJECT_ID"

# Enable required APIs
echo "Enabling Google Cloud APIs..."
gcloud services enable \
    aiplatform.googleapis.com \
    pubsub.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    bigquery.googleapis.com \
    storage.googleapis.com \
    --project=$PROJECT_ID

# Create service account
echo "Creating service account..."
gcloud iam service-accounts create cx-rescue-swarm \
    --display-name="Customer Experience Rescue Swarm" \
    --description="Service account for CX Rescue Swarm application" \
    --project=$PROJECT_ID

# Assign IAM roles
echo "Assigning IAM roles..."
SERVICE_ACCOUNT="cx-rescue-swarm@$PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/storage.objectViewer"

# Create Pub/Sub topic and subscription
echo "Creating Pub/Sub topic and subscription..."
gcloud pubsub topics create high_negative_sentiment_alerts --project=$PROJECT_ID

gcloud pubsub subscriptions create cx-swarm-subscription \
    --topic=high_negative_sentiment_alerts \
    --project=$PROJECT_ID

# Create BigQuery dataset and tables
echo "Creating BigQuery dataset..."
bq mk --dataset --location=$REGION $PROJECT_ID:customer_data

# Create transcript table
echo "Creating BigQuery tables..."
bq mk --table $PROJECT_ID:customer_data.call_transcripts \
    transcript_id:STRING,customer_id:STRING,transcript_text:STRING,created_at:TIMESTAMP,sentiment_score:FLOAT

bq mk --table $PROJECT_ID:customer_data.transcript_analysis \
    transcript_id:STRING,analysis_timestamp:TIMESTAMP,sentiment_score:FLOAT,escalated:BOOLEAN,resolution_taken:STRING,agent_notes:STRING

# Create Cloud Storage bucket for transcripts
echo "Creating Cloud Storage bucket..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$PROJECT_ID-transcripts

# Create placeholder secrets (you'll need to update these with actual values)
echo "Creating placeholder secrets..."
echo "placeholder-crm-key" | gcloud secrets create crm-api-key --data-file=- --project=$PROJECT_ID
echo "placeholder-inventory-key" | gcloud secrets create inventory-api-key --data-file=- --project=$PROJECT_ID
echo "placeholder-payment-key" | gcloud secrets create payment-api-key --data-file=- --project=$PROJECT_ID
echo "placeholder-sendgrid-key" | gcloud secrets create sendgrid-api-key --data-file=- --project=$PROJECT_ID
echo "placeholder-twilio-token" | gcloud secrets create twilio-auth-token --data-file=- --project=$PROJECT_ID

echo "Setup complete! Don't forget to:"
echo "1. Update the secrets with actual API keys"
echo "2. Configure your external APIs to point to the correct endpoints"
echo "3. Set up Vector Search index for policy documents"
echo "4. Deploy the application using: gcloud run deploy"