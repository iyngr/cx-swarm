# Customer Experience Rescue Swarm

A multi-agent system built on Google Cloud's Agent Engine that automatically resolves critical customer complaints based on negative sentiment analysis.

## Overview

The Customer Experience Rescue (CX-Rescue) Swarm is designed to automatically identify, analyze, and resolve critical customer issues before they escalate. When triggered by high negative sentiment scores from call transcripts, the system orchestrates a three-agent workflow to restore customer confidence.

## Architecture

### High-Level Flow
1. **Trigger**: Pub/Sub message from upstream sentiment analysis
2. **Triage Agent**: Validates alert and gathers customer context
3. **Solution Agent**: Determines resolution using company policies (RAG)
4. **Action Agent**: Executes solution and communicates with customer

### Technology Stack
- **Google Cloud Agent Engine**: Orchestration platform
- **Vertex AI**: LLM processing (Gemini 1.5 Pro)
- **Vector Search**: RAG knowledge base for policies
- **Pub/Sub**: Event triggering
- **Secret Manager**: Secure credential storage
- **Cloud Run**: Serverless deployment

## Quick Start

### Prerequisites
- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Python 3.11+

### Setup

1. **Clone and setup the project**:
   ```bash
   git clone <repository-url>
   cd cx-swarm
   pip install -r requirements.txt
   ```

2. **Configure Google Cloud**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ./setup-gcp.sh $GOOGLE_CLOUD_PROJECT
   ```

3. **Update secrets with real API keys**:
   ```bash
   # Update each secret with actual API keys
   echo "your-crm-api-key" | gcloud secrets versions add crm-api-key --data-file=-
   echo "your-inventory-api-key" | gcloud secrets versions add inventory-api-key --data-file=-
   echo "your-stripe-api-key" | gcloud secrets versions add payment-api-key --data-file=-
   echo "your-sendgrid-api-key" | gcloud secrets versions add sendgrid-api-key --data-file=-
   echo "your-twilio-token" | gcloud secrets versions add twilio-auth-token --data-file=-
   ```

4. **Prepare knowledge base**:
   ```bash
   python knowledge_base/prepare_knowledge_base.py
   ```

5. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy cx-rescue-swarm \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

## Components

### Agents

#### 1. Triage Agent (`agents/triage_agent.py`)
**Purpose**: Validates incoming alerts and determines if escalation is warranted.

**Tools**:
- `CRMLookupTool`: Fetches customer data and LTV
- `TranscriptRetrievalTool`: Retrieves call transcripts

**Decision Criteria**:
- Customer value: LTV > $500 OR Gold/VIP status
- Transcript severity: Explicit dissatisfaction phrases
- High sentiment score confirmation

#### 2. Solution Agent (`agents/solution_agent.py`)
**Purpose**: Determines optimal resolution path using company policies.

**Tools**:
- `PolicyLookupTool`: RAG-based policy search
- `OrderStatusTool`: Real-time order information
- `InventoryCheckTool`: Product availability

**Output**: Ranked list of concrete solutions with parameters.

#### 3. Action Agent (`agents/action_agent.py`)
**Purpose**: Executes solutions and communicates with customers.

**Tools**:
- Payment tools: Refunds, coupons, account credits
- Shipping tools: Reshipment, expedited delivery
- Communication tools: Email, SMS notifications
- CRM logging: Incident documentation

### Tools

#### CRM Integration (`tools/crm_lookup_tool.py`)
- Customer data retrieval
- Account note updates
- Service history access

#### Policy Knowledge Base (`tools/policy_lookup_tool.py`)
- Vector similarity search
- Semantic policy matching
- Context-aware recommendations

#### Payment Processing (`tools/payment_tools.py`)
- Stripe integration for refunds
- Coupon generation
- Account credit management

#### Communication (`tools/communication_tools.py`)
- SendGrid email delivery
- Twilio SMS notifications
- Personalized content generation

## Configuration

### Environment Variables
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
CRM_API_BASE_URL=https://api.yourcrm.com
INVENTORY_API_BASE_URL=https://api.yourinventory.com
PAYMENT_API_BASE_URL=https://api.stripe.com
SENDGRID_FROM_EMAIL=support@yourcompany.com
```

### Secret Manager Secrets
- `crm-api-key`: CRM system API key
- `inventory-api-key`: Inventory/order system API key  
- `payment-api-key`: Payment processor API key
- `sendgrid-api-key`: Email service API key
- `twilio-auth-token`: SMS service authentication

## Message Format

The system expects Pub/Sub messages in this format:
```json
{
  "transcript_id": "T12345",
  "customer_id": "C67890", 
  "sentiment_score": 0.95
}
```

## Policy Knowledge Base

### Document Structure
Company policies should be organized as:
- Refund policies (by customer tier)
- Shipping compensation guidelines
- Product issue resolution procedures
- Escalation matrices
- Appeasement authority levels

### Adding New Policies
1. Add documents to `knowledge_base/policies/`
2. Run `python knowledge_base/prepare_knowledge_base.py`
3. Update Vector Search index

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Test individual components:
```bash
pytest tests/test_triage_agent.py -v
pytest tests/test_solution_agent.py -v
pytest tests/test_action_agent.py -v
```

## Monitoring and Logging

### Cloud Logging
All agent actions are logged with structured data:
- Customer ID and issue details
- Agent decisions and reasoning
- Solution execution results
- Communication delivery status

### Metrics to Monitor
- Alert processing time
- Escalation rates by customer tier
- Solution success rates
- Customer satisfaction post-resolution

## Security

### Best Practices Implemented
- All API keys stored in Secret Manager
- Service account with minimal required permissions
- Input validation and sanitization
- Secure communication channels (HTTPS/TLS)
- Audit logging for all customer interactions

### IAM Roles Required
- `roles/aiplatform.user`: Vertex AI access
- `roles/secretmanager.secretAccessor`: Secret retrieval
- `roles/pubsub.subscriber`: Message processing
- `roles/bigquery.dataViewer`: Transcript access

## Troubleshooting

### Common Issues

1. **Agent initialization fails**:
   - Verify Google Cloud credentials
   - Check service account permissions
   - Confirm API enablement

2. **Policy lookup returns no results**:
   - Verify Vector Search index exists
   - Check embedding model availability
   - Validate knowledge base preparation

3. **External API calls fail**:
   - Verify API keys in Secret Manager
   - Check API endpoint configurations
   - Review network connectivity

### Debug Mode
Set environment variable for verbose logging:
```bash
export LOG_LEVEL=DEBUG
```

## Extending the System

### Adding New Resolution Actions
1. Create new tool in `tools/` directory
2. Add action handler in `ActionAgent._execute_solution()`
3. Update solution generation prompts
4. Add corresponding tests

### Adding New Data Sources
1. Implement new tool following existing patterns
2. Add to relevant agent initialization
3. Update agent prompts to utilize new data
4. Configure required API access

## Performance Considerations

### Optimization Strategies
- Batch API calls where possible
- Cache frequently accessed data
- Use async processing for I/O operations
- Implement request rate limiting

### Scaling
- Cloud Run auto-scales based on demand
- Pub/Sub provides reliable message queuing
- Vector Search handles high query volumes
- Consider regional deployment for global coverage

## Cost Management

### Resource Usage
- Vertex AI LLM calls: $0.02-0.05 per 1K tokens
- Vector Search queries: $0.001 per query
- Cloud Run: Pay-per-request with generous free tier
- Storage: Minimal for transcripts and policies

### Cost Optimization
- Tune LLM prompts for conciseness
- Implement caching for repeated queries
- Use regional resources to minimize latency
- Monitor and alert on usage spikes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.