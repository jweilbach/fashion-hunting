"""
Unit tests for AnalyticsService.

These tests mock the repository layer to test service logic in isolation.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from services.analytics_service import AnalyticsService


class TestAnalyticsService:
    """Test cases for AnalyticsService"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_report_repo(self):
        """Mock report repository."""
        return MagicMock()

    @pytest.fixture
    def mock_brand_repo(self):
        """Mock brand repository."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_report_repo, mock_brand_repo):
        """Create AnalyticsService with mocked dependencies."""
        return AnalyticsService(
            db=mock_db,
            report_repo=mock_report_repo,
            brand_repo=mock_brand_repo
        )

    @pytest.fixture
    def tenant_id(self):
        """Generate a test tenant ID."""
        return uuid4()

    # =========================================================================
    # get_sentiment_analysis tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_sentiment_analysis_returns_correct_structure(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that sentiment analysis returns the expected structure."""
        mock_report_repo.get_sentiment_stats.return_value = {
            "positive": 50,
            "neutral": 30,
            "negative": 20
        }

        result = service.get_sentiment_analysis(tenant_id, days=30)

        assert "period_days" in result
        assert "total_reports" in result
        assert "sentiment_counts" in result
        assert "sentiment_percentages" in result
        assert "start_date" in result
        assert "end_date" in result

    @pytest.mark.unit
    def test_get_sentiment_analysis_calculates_correct_percentages(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that percentages are calculated correctly."""
        mock_report_repo.get_sentiment_stats.return_value = {
            "positive": 50,
            "neutral": 30,
            "negative": 20
        }

        result = service.get_sentiment_analysis(tenant_id, days=30)

        assert result["total_reports"] == 100
        assert result["sentiment_percentages"]["positive"] == 50.0
        assert result["sentiment_percentages"]["neutral"] == 30.0
        assert result["sentiment_percentages"]["negative"] == 20.0

    @pytest.mark.unit
    def test_get_sentiment_analysis_handles_zero_reports(
        self, service, mock_report_repo, tenant_id
    ):
        """Test handling of zero reports (no division by zero)."""
        mock_report_repo.get_sentiment_stats.return_value = {
            "positive": 0,
            "neutral": 0,
            "negative": 0
        }

        result = service.get_sentiment_analysis(tenant_id, days=30)

        assert result["total_reports"] == 0
        assert result["sentiment_percentages"]["positive"] == 0
        assert result["sentiment_percentages"]["neutral"] == 0
        assert result["sentiment_percentages"]["negative"] == 0

    # =========================================================================
    # get_top_brands tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_top_brands_returns_ranked_list(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that top brands are returned with correct rankings."""
        mock_report_repo.get_top_brands.return_value = [
            ("BrandA", 100),
            ("BrandB", 75),
            ("BrandC", 50)
        ]

        result = service.get_top_brands(tenant_id, days=30, limit=10)

        assert len(result) == 3
        assert result[0]["brand"] == "BrandA"
        assert result[0]["mention_count"] == 100
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 3

    @pytest.mark.unit
    def test_get_top_brands_empty_list(
        self, service, mock_report_repo, tenant_id
    ):
        """Test handling of empty brand list."""
        mock_report_repo.get_top_brands.return_value = []

        result = service.get_top_brands(tenant_id, days=30, limit=10)

        assert result == []

    # =========================================================================
    # get_daily_report_counts tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_daily_report_counts_formats_correctly(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that daily counts are formatted correctly."""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        mock_report_repo.get_daily_counts.return_value = [
            (today, 10, 5000),
            (yesterday, 8, 4000)
        ]

        result = service.get_daily_report_counts(tenant_id, days=30)

        assert len(result) == 2
        assert result[0]["date"] == today.isoformat()
        assert result[0]["report_count"] == 10
        assert result[0]["avg_reach"] == 5000

    @pytest.mark.unit
    def test_get_daily_report_counts_handles_null_reach(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that null avg_reach is converted to 0."""
        today = datetime.now().date()

        mock_report_repo.get_daily_counts.return_value = [
            (today, 5, None)
        ]

        result = service.get_daily_report_counts(tenant_id, days=30)

        assert result[0]["avg_reach"] == 0

    # =========================================================================
    # get_provider_breakdown tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_provider_breakdown_calculates_percentages(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that provider breakdown calculates percentages correctly."""
        mock_report_repo.get_provider_stats.return_value = {
            "google_search": {"report_count": 60, "total_reach": 100000},
            "instagram": {"report_count": 40, "total_reach": 50000}
        }

        result = service.get_provider_breakdown(tenant_id, days=30)

        assert result["total_reports"] == 100
        assert result["total_reach"] == 150000
        assert result["providers"]["google_search"]["report_percentage"] == 60.0
        assert result["providers"]["instagram"]["report_percentage"] == 40.0

    @pytest.mark.unit
    def test_get_provider_breakdown_handles_empty_stats(
        self, service, mock_report_repo, tenant_id
    ):
        """Test handling of empty provider stats."""
        mock_report_repo.get_provider_stats.return_value = {}

        result = service.get_provider_breakdown(tenant_id, days=30)

        assert result["total_reports"] == 0
        assert result["total_reach"] == 0
        assert result["providers"] == {}

    # =========================================================================
    # get_analytics_summary tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_analytics_summary_returns_comprehensive_data(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that analytics summary returns all expected fields."""
        mock_report_repo.get_sentiment_stats.return_value = {
            "positive": 50, "neutral": 30, "negative": 20
        }
        mock_report_repo.get_top_brands.return_value = [("BrandA", 100)]
        mock_report_repo.get_provider_stats.return_value = {
            "google_search": {"report_count": 100, "total_reach": 100000}
        }

        result = service.get_analytics_summary(tenant_id, days=30)

        assert "period_days" in result
        assert "total_reports" in result
        assert "avg_daily_reports" in result
        assert "total_estimated_reach" in result
        assert "sentiment" in result
        assert "top_brands" in result
        assert "providers" in result

    @pytest.mark.unit
    def test_get_analytics_summary_calculates_avg_daily_correctly(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that average daily reports is calculated correctly."""
        mock_report_repo.get_sentiment_stats.return_value = {
            "positive": 30, "neutral": 20, "negative": 10
        }
        mock_report_repo.get_top_brands.return_value = []
        mock_report_repo.get_provider_stats.return_value = {}

        result = service.get_analytics_summary(tenant_id, days=30)

        # Total is 60, over 30 days = 2.0 per day
        assert result["avg_daily_reports"] == 2.0

    # =========================================================================
    # get_trends tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_trends_identifies_upward_trend(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that upward trends are correctly identified."""
        # Current week: 100 reports
        # Previous week (14 days total - 7 current = 50): 50 reports
        mock_report_repo.get_sentiment_stats.side_effect = [
            {"positive": 60, "neutral": 30, "negative": 10},  # 7 days
            {"positive": 90, "neutral": 45, "negative": 15},  # 14 days
        ]
        mock_report_repo.get_top_brands.return_value = []

        result = service.get_trends(tenant_id)

        assert result["changes"]["trend"] == "up"
        assert result["current_week"]["total_reports"] == 100
        assert result["previous_week"]["total_reports"] == 50

    @pytest.mark.unit
    def test_get_trends_identifies_downward_trend(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that downward trends are correctly identified."""
        # Current week: 50 reports
        # Previous week: 100 reports
        mock_report_repo.get_sentiment_stats.side_effect = [
            {"positive": 30, "neutral": 15, "negative": 5},   # 7 days = 50
            {"positive": 90, "neutral": 45, "negative": 15},  # 14 days = 150
        ]
        mock_report_repo.get_top_brands.return_value = []

        result = service.get_trends(tenant_id)

        assert result["changes"]["trend"] == "down"

    @pytest.mark.unit
    def test_get_trends_identifies_stable_trend(
        self, service, mock_report_repo, tenant_id
    ):
        """Test that stable trends are correctly identified."""
        # Both weeks: 50 reports
        mock_report_repo.get_sentiment_stats.side_effect = [
            {"positive": 30, "neutral": 15, "negative": 5},   # 7 days = 50
            {"positive": 60, "neutral": 30, "negative": 10},  # 14 days = 100
        ]
        mock_report_repo.get_top_brands.return_value = []

        result = service.get_trends(tenant_id)

        assert result["changes"]["trend"] == "stable"
        assert result["changes"]["volume_change"] == 0


class TestAnalyticsServiceEdgeCases:
    """Edge case tests for AnalyticsService"""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_db = MagicMock()
        mock_report_repo = MagicMock()
        mock_brand_repo = MagicMock()
        return AnalyticsService(
            db=mock_db,
            report_repo=mock_report_repo,
            brand_repo=mock_brand_repo
        )

    @pytest.mark.unit
    def test_service_uses_default_repos_when_not_provided(self):
        """Test that service creates default repos when not provided."""
        mock_db = MagicMock()

        with patch('services.analytics_service.ReportRepository') as mock_report_class:
            with patch('services.analytics_service.BrandRepository') as mock_brand_class:
                service = AnalyticsService(db=mock_db)

                mock_report_class.assert_called_once_with(mock_db)
                mock_brand_class.assert_called_once_with(mock_db)

    @pytest.mark.unit
    def test_handles_large_numbers(self, service):
        """Test handling of large reach numbers."""
        service.report_repo.get_provider_stats.return_value = {
            "youtube": {"report_count": 1000, "total_reach": 1_000_000_000}
        }
        tenant_id = uuid4()

        result = service.get_provider_breakdown(tenant_id, days=30)

        assert result["total_reach"] == 1_000_000_000
