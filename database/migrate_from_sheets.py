"""
Migration script to move data from Google Sheets to PostgreSQL
Handles incremental migration and deduplication
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yaml
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
load_dotenv()


class SheetsMigrator:
    """Migrates data from Google Sheets to PostgreSQL"""

    def __init__(self, tenant_slug: str = 'abmc-demo'):
        self.tenant_slug = tenant_slug
        self.tenant_id = None
        self.conn = None
        self.sheets_client = None

    def connect_to_db(self):
        """Connect to PostgreSQL database"""
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'abmc_reports'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }

        try:
            self.conn = psycopg2.connect(**conn_params)
            print(f"✓ Connected to PostgreSQL database: {conn_params['database']}")
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            raise

    def connect_to_sheets(self):
        """Connect to Google Sheets"""
        try:
            # Load service account credentials
            creds_path = Path(__file__).parent.parent / "gcp_service_account.json"

            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Google service account file not found: {creds_path}\n"
                    "Please ensure gcp_service_account.json exists in the project root"
                )

            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]

            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                str(creds_path), scope
            )
            self.sheets_client = gspread.authorize(credentials)

            print(f"✓ Connected to Google Sheets")

        except Exception as e:
            print(f"✗ Failed to connect to Google Sheets: {e}")
            raise

    def get_or_create_tenant(self) -> str:
        """Get or create tenant in database"""
        cursor = self.conn.cursor()

        try:
            # Try to find existing tenant
            cursor.execute("SELECT id FROM tenants WHERE slug = %s", (self.tenant_slug,))
            result = cursor.fetchone()

            if result:
                self.tenant_id = result[0]
                print(f"✓ Found existing tenant: {self.tenant_slug} (ID: {self.tenant_id})")
            else:
                # Create new tenant
                cursor.execute("""
                    INSERT INTO tenants (slug, name, email, company_name)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.tenant_slug,
                    self.tenant_slug.replace('-', ' ').title(),
                    f"{self.tenant_slug}@example.com",
                    "Migrated Account"
                ))
                self.tenant_id = cursor.fetchone()[0]
                self.conn.commit()
                print(f"✓ Created new tenant: {self.tenant_slug} (ID: {self.tenant_id})")

            cursor.close()
            return self.tenant_id

        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error getting/creating tenant: {e}")
            raise

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from YAML config files"""
        try:
            settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"

            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = yaml.safe_load(f)
                    print(f"✓ Loaded settings from {settings_path}")
                    return settings
            else:
                print("⚠ No settings.yaml found, using defaults")
                return {}

        except Exception as e:
            print(f"⚠ Error loading settings: {e}, using defaults")
            return {}

    def migrate_sheet_data(self, sheet_id: str, worksheet_name: str = None) -> int:
        """
        Migrate data from a Google Sheet to PostgreSQL

        Args:
            sheet_id: Google Sheet ID
            worksheet_name: Specific worksheet name (optional)

        Returns:
            Number of rows migrated
        """
        try:
            # Open the spreadsheet
            spreadsheet = self.sheets_client.open_by_key(sheet_id)
            print(f"✓ Opened spreadsheet: {spreadsheet.title}")

            # List available worksheets
            worksheets = spreadsheet.worksheets()
            print(f"  Available worksheets:")
            for ws in worksheets:
                print(f"    - '{ws.title}'")

            # Get worksheet
            if worksheet_name:
                try:
                    worksheet = spreadsheet.worksheet(worksheet_name)
                except Exception as e:
                    print(f"✗ Worksheet '{worksheet_name}' not found")
                    print(f"  Trying first worksheet instead...")
                    worksheet = spreadsheet.sheet1
            else:
                worksheet = spreadsheet.sheet1

            print(f"✓ Using worksheet: '{worksheet.title}'")

            # Get all records
            records = worksheet.get_all_records()
            print(f"✓ Found {len(records)} rows in sheet")

            if len(records) == 0:
                print("⚠ No data to migrate")
                return 0

            # Migrate records
            migrated_count = self._migrate_records(records)

            return migrated_count

        except Exception as e:
            print(f"✗ Error migrating sheet data: {e}")
            raise

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if not timestamp_str or timestamp_str == '':
            return None

        # Try ISO 8601 format first (with timezone)
        try:
            from dateutil import parser
            return parser.isoparse(timestamp_str)
        except:
            pass

        # Try different timestamp formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # If all formats fail, return None
        print(f"⚠ Could not parse timestamp: {timestamp_str}")
        return None

    def _parse_brands(self, brands_str: str) -> List[str]:
        """Parse brands from comma-separated string"""
        if not brands_str or brands_str == '':
            return []

        # Split by comma and strip whitespace
        brands = [b.strip() for b in brands_str.split(',') if b.strip()]
        return brands

    def _parse_int(self, value: Any, default: int = 0) -> int:
        """Safely parse integer value"""
        if value == '' or value is None:
            return default

        try:
            return int(float(value))  # Handle '100.0' -> 100
        except (ValueError, TypeError):
            return default

    def _migrate_records(self, records: List[Dict[str, Any]]) -> int:
        """Migrate records to database"""
        cursor = self.conn.cursor()
        migrated = 0
        skipped = 0
        errors = 0

        # Common column mappings from Google Sheets (case-insensitive)
        column_mappings = {
            'timestamp': 'timestamp',
            'date': 'timestamp',
            'source': 'source',
            'brands': 'brands',
            'brand': 'brands',
            'title': 'title',
            'link': 'link',
            'url': 'link',
            'summary': 'summary',
            'full text': 'full_text',
            'sentiment': 'sentiment',
            'topic': 'topic',
            'est. reach': 'est_reach',
            'est_reach': 'est_reach',
            'estimated reach': 'est_reach',
        }

        for idx, record in enumerate(records, start=1):
            try:
                # Map columns (normalize keys to lowercase for case-insensitive matching)
                mapped_record = {}
                for sheet_col, db_col in column_mappings.items():
                    # Try exact match first, then case-insensitive
                    if sheet_col in record:
                        mapped_record[db_col] = record[sheet_col]
                    else:
                        # Case-insensitive match
                        for key in record.keys():
                            if key.lower() == sheet_col.lower():
                                mapped_record[db_col] = record[key]
                                break

                # Parse required fields
                timestamp = self._parse_timestamp(
                    mapped_record.get('timestamp', '')
                )
                if not timestamp:
                    timestamp = datetime.now()  # Default to now if no timestamp

                title = mapped_record.get('title', '').strip()
                link = mapped_record.get('link', '').strip()

                # Skip if missing required fields
                if not title or not link:
                    skipped += 1
                    continue

                # Parse optional fields
                source = mapped_record.get('source', 'RSS')
                brands = self._parse_brands(mapped_record.get('brands', ''))
                summary = mapped_record.get('summary', '')
                full_text = mapped_record.get('full_text', '')
                sentiment = mapped_record.get('sentiment', '').lower()
                topic = mapped_record.get('topic', '')
                est_reach = self._parse_int(mapped_record.get('est_reach', 0))

                # Determine provider from source
                provider = 'RSS'
                if 'tiktok' in source.lower():
                    provider = 'TikTok'
                elif 'instagram' in source.lower():
                    provider = 'Instagram'

                # Insert into database (dedupe_key is auto-generated by trigger)
                cursor.execute("""
                    INSERT INTO reports (
                        tenant_id,
                        timestamp,
                        source,
                        provider,
                        brands,
                        title,
                        link,
                        summary,
                        full_text,
                        sentiment,
                        topic,
                        est_reach,
                        processing_status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed'
                    )
                    ON CONFLICT (tenant_id, dedupe_key) DO NOTHING
                """, (
                    self.tenant_id,
                    timestamp,
                    source,
                    provider,
                    brands,
                    title,
                    link,
                    summary,
                    full_text,
                    sentiment if sentiment in ['positive', 'neutral', 'negative', 'mixed'] else None,
                    topic,
                    est_reach
                ))

                if cursor.rowcount > 0:
                    migrated += 1
                else:
                    skipped += 1  # Duplicate

                # Commit every 100 rows
                if idx % 100 == 0:
                    self.conn.commit()
                    print(f"  Progress: {idx}/{len(records)} rows processed "
                          f"({migrated} migrated, {skipped} skipped, {errors} errors)")

            except Exception as e:
                errors += 1
                print(f"  ✗ Error migrating row {idx}: {e}")
                # Continue with next record

        # Final commit
        self.conn.commit()
        cursor.close()

        print(f"\n✓ Migration completed:")
        print(f"  - Migrated: {migrated}")
        print(f"  - Skipped (duplicates/invalid): {skipped}")
        print(f"  - Errors: {errors}")

        return migrated

    def migrate_brand_configs(self, settings: Dict[str, Any]):
        """Migrate brand configurations from settings"""
        cursor = self.conn.cursor()

        try:
            known_brands = settings.get('known_brands', [])
            ignore_brands = settings.get('ignore_brand_exact', [])

            print(f"\nMigrating brand configurations...")
            print(f"  - Known brands: {len(known_brands)}")
            print(f"  - Ignored brands: {len(ignore_brands)}")

            # Migrate known brands
            for brand in known_brands:
                cursor.execute("""
                    INSERT INTO brand_configs (tenant_id, brand_name, is_known_brand, category)
                    VALUES (%s, %s, true, 'client')
                    ON CONFLICT (tenant_id, brand_name) DO NOTHING
                """, (self.tenant_id, brand))

            # Migrate ignored brands
            for brand in ignore_brands:
                cursor.execute("""
                    INSERT INTO brand_configs (tenant_id, brand_name, should_ignore)
                    VALUES (%s, %s, true)
                    ON CONFLICT (tenant_id, brand_name)
                    DO UPDATE SET should_ignore = true
                """, (self.tenant_id, brand))

            self.conn.commit()
            cursor.close()

            print(f"✓ Brand configurations migrated")

        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error migrating brand configs: {e}")
            raise

    def migrate_feed_configs(self, feeds: List[str]):
        """Migrate feed configurations"""
        cursor = self.conn.cursor()

        try:
            print(f"\nMigrating {len(feeds)} feed configurations...")

            for feed_url in feeds:
                # Extract label from URL
                label = feed_url.split('/')[-1][:100] if feed_url else 'RSS Feed'

                cursor.execute("""
                    INSERT INTO feed_configs (
                        tenant_id, provider, feed_type, feed_value, label
                    )
                    VALUES (%s, 'RSS', 'rss_url', %s, %s)
                    ON CONFLICT DO NOTHING
                """, (self.tenant_id, feed_url, label))

            self.conn.commit()
            cursor.close()

            print(f"✓ Feed configurations migrated")

        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error migrating feed configs: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("\n✓ Database connection closed")


def main():
    """Main migration flow"""
    print("="*60)
    print("ABMC Phase 1 - Google Sheets to PostgreSQL Migration")
    print("="*60)

    # Get configuration from environment
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    worksheet_name = os.getenv('WORKSHEET_NAME')
    tenant_slug = os.getenv('TENANT_SLUG', 'abmc-demo')

    if not sheet_id:
        print("\n✗ Error: GOOGLE_SHEET_ID environment variable not set")
        print("Please set GOOGLE_SHEET_ID in your .env file")
        sys.exit(1)

    migrator = SheetsMigrator(tenant_slug=tenant_slug)

    try:
        # Step 1: Connect to services
        print("\n1. Connecting to services...")
        migrator.connect_to_db()
        migrator.connect_to_sheets()

        # Step 2: Get or create tenant
        print("\n2. Setting up tenant...")
        migrator.get_or_create_tenant()

        # Step 3: Load settings
        print("\n3. Loading configuration...")
        settings = migrator.load_settings()

        # Step 4: Migrate brand configs
        if settings:
            migrator.migrate_brand_configs(settings)

        # Step 5: Migrate feed configs
        feeds_path = Path(__file__).parent.parent / "config" / "feeds.yaml"
        if feeds_path.exists():
            with open(feeds_path, 'r') as f:
                feeds_data = yaml.safe_load(f)
                feeds = feeds_data.get('feeds', []) if isinstance(feeds_data, dict) else feeds_data
                migrator.migrate_feed_configs(feeds)

        # Step 6: Migrate sheet data
        print("\n4. Migrating data from Google Sheets...")
        migrated_count = migrator.migrate_sheet_data(sheet_id, worksheet_name)

        # Success
        print("\n" + "="*60)
        print(f"✓ Migration completed successfully!")
        print(f"  Total records migrated: {migrated_count}")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
