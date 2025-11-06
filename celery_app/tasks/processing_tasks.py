"""
Celery tasks for processing reports with OpenAI
"""
import sys
from pathlib import Path
from typing import Dict, Any, List
import json
from uuid import UUID
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from celery_app.celery import app
from models.base import SessionLocal
from repositories.report_repository import ReportRepository
from repositories.brand_repository import BrandRepository
from openai import OpenAI


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


@app.task(name='celery_app.tasks.processing_tasks.process_report')
def process_report(report_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Process a report with OpenAI to extract brands and sentiment
    
    Args:
        report_id: UUID of the report
        tenant_id: UUID of the tenant
        
    Returns:
        Dict with processing results
    """
    db = SessionLocal()
    results = {
        'report_id': report_id,
        'status': 'pending',
        'brands_extracted': 0,
        'sentiment': None,
        'topic': None,
        'error': None
    }
    
    try:
        report_repo = ReportRepository(db)
        brand_repo = BrandRepository(db)
        
        # Get report
        report = report_repo.get_by_id(UUID(report_id))
        if not report:
            results['error'] = 'Report not found'
            results['status'] = 'failed'
            return results
        
        # Prepare content for OpenAI
        content = f"Title: {report.title}\n\nSummary: {report.summary or ''}"
        
        # Call OpenAI for brand extraction and sentiment analysis
        system_prompt = """You are a PR and media analyst. Analyze the given article and extract:
1. Brand names mentioned (companies, products, organizations)
2. Sentiment towards each brand or overall (positive, neutral, negative, mixed)
3. Topic/category (product_launch, partnership, controversy, trend, awards, campaign, other)

Return a JSON object with:
{
  "brands": ["Brand1", "Brand2"],
  "sentiment": "positive|neutral|negative|mixed",
  "topic": "product_launch|partnership|controversy|trend|awards|campaign|other",
  "reasoning": "brief explanation"
}"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse OpenAI response
            ai_result = json.loads(response.choices[0].message.content)
            
            brands = ai_result.get('brands', [])
            sentiment = ai_result.get('sentiment', 'neutral')
            topic = ai_result.get('topic', 'other')
            reasoning = ai_result.get('reasoning', '')
            
            # Update report
            report_repo.update(
                UUID(report_id),
                brands=brands,
                sentiment=sentiment,
                topic=topic,
                processing_status='completed',
                metadata={'ai_reasoning': reasoning}
            )
            
            # Update brand mention counts
            for brand_name in brands:
                try:
                    brand_repo.increment_mention_count(
                        UUID(tenant_id),
                        brand_name,
                        report.timestamp
                    )
                except Exception as e:
                    # Create brand if it doesn't exist
                    try:
                        brand_repo.get_or_create(
                            UUID(tenant_id),
                            brand_name,
                            is_known_brand=False,
                            category='discovered'
                        )
                        brand_repo.increment_mention_count(
                            UUID(tenant_id),
                            brand_name,
                            report.timestamp
                        )
                    except:
                        pass
            
            results['brands_extracted'] = len(brands)
            results['sentiment'] = sentiment
            results['topic'] = topic
            results['status'] = 'completed'
            
        except Exception as e:
            results['error'] = f"OpenAI error: {str(e)}"
            results['status'] = 'failed'
            
            # Mark report as failed
            report_repo.update(
                UUID(report_id),
                processing_status='failed',
                metadata={'error': str(e)}
            )
    
    except Exception as e:
        results['error'] = f"Processing error: {str(e)}"
        results['status'] = 'failed'
    
    finally:
        db.close()
    
    return results


@app.task(name='celery_app.tasks.processing_tasks.reprocess_report')
def reprocess_report(report_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Reprocess a report (useful for failed reports or re-analysis)
    
    Args:
        report_id: UUID of the report
        tenant_id: UUID of the tenant
        
    Returns:
        Dict with processing results
    """
    db = SessionLocal()
    
    try:
        report_repo = ReportRepository(db)
        
        # Reset report status to pending
        report_repo.update(
            UUID(report_id),
            processing_status='pending',
            brands=[],
            sentiment=None,
            topic=None,
            metadata={}
        )
        
        db.commit()
    finally:
        db.close()
    
    # Process the report
    return process_report(report_id, tenant_id)


@app.task(name='celery_app.tasks.processing_tasks.batch_process_pending')
def batch_process_pending(tenant_id: str, limit: int = 50) -> Dict[str, Any]:
    """
    Process all pending reports for a tenant
    
    Args:
        tenant_id: UUID of the tenant
        limit: Maximum number of reports to process
        
    Returns:
        Summary of batch processing
    """
    db = SessionLocal()
    results = {
        'tenant_id': tenant_id,
        'processed': 0,
        'successful': 0,
        'failed': 0
    }
    
    try:
        report_repo = ReportRepository(db)
        
        # Get pending reports
        pending_reports = report_repo.get_all(
            tenant_id=UUID(tenant_id),
            status='pending',
            limit=limit
        )
        
        results['processed'] = len(pending_reports)
        
        # Process each report
        for report in pending_reports:
            try:
                result = process_report.delay(str(report.id), tenant_id).get(timeout=60)
                if result['status'] == 'completed':
                    results['successful'] += 1
                else:
                    results['failed'] += 1
            except Exception:
                results['failed'] += 1
    
    finally:
        db.close()
    
    return results
