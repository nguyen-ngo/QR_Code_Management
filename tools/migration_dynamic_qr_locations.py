"""
Migration: Dynamic QR Code Support
====================================
Applies the following database changes required for the Dynamic QR feature:

  1. Adds qr_type column to qr_codes           (VARCHAR 20, default 'standard')
  2. Creates qr_code_locations table
  3. Makes qr_codes.location nullable           (was NOT NULL)
  4. Makes qr_codes.location_address nullable   (was NOT NULL)

Usage (run once from the project root):
    python tools/migration_dynamic_qr_locations.py

Fully idempotent — safe to run multiple times without side effects.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db


def run_migration():
    with app.app_context():
        from sqlalchemy import text, inspect as sa_inspect

        inspector = sa_inspect(db.engine)

        # ----------------------------------------------------------------
        # Step 1: Add qr_type column to qr_codes if it does not exist yet
        # ----------------------------------------------------------------
        existing_cols = {c['name'] for c in inspector.get_columns('qr_codes')}

        if 'qr_type' not in existing_cols:
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE qr_codes "
                    "ADD COLUMN qr_type VARCHAR(20) NOT NULL DEFAULT 'standard'"
                ))
                conn.commit()
            print("✅  Added column: qr_codes.qr_type  (default = 'standard')")
        else:
            print("ℹ️   Column qr_codes.qr_type already exists — skipped.")

        # ----------------------------------------------------------------
        # Step 2: Create qr_code_locations table if it does not exist yet
        # ----------------------------------------------------------------
        existing_tables = set(inspector.get_table_names())

        if 'qr_code_locations' not in existing_tables:
            from models.qrcode import QRCodeLocation
            QRCodeLocation.__table__.create(db.engine, checkfirst=True)
            print("✅  Created table: qr_code_locations")
        else:
            print("ℹ️   Table qr_code_locations already exists — skipped.")

        # ----------------------------------------------------------------
        # Step 3: Make qr_codes.location and location_address nullable
        # Dynamic QR codes have no single fixed location/address so these
        # columns must allow NULL.
        # ----------------------------------------------------------------
        # Re-inspect to get current column definitions
        inspector2 = sa_inspect(db.engine)
        col_map = {c['name']: c for c in inspector2.get_columns('qr_codes')}

        location_nullable     = col_map.get('location', {}).get('nullable', True)
        loc_addr_nullable     = col_map.get('location_address', {}).get('nullable', True)

        if not location_nullable or not loc_addr_nullable:
            with db.engine.connect() as conn:
                if not location_nullable:
                    conn.execute(text(
                        "ALTER TABLE qr_codes "
                        "MODIFY COLUMN location VARCHAR(100) NULL"
                    ))
                    print("✅  Made qr_codes.location nullable")
                else:
                    print("ℹ️   qr_codes.location already nullable — skipped.")

                if not loc_addr_nullable:
                    conn.execute(text(
                        "ALTER TABLE qr_codes "
                        "MODIFY COLUMN location_address TEXT NULL"
                    ))
                    print("✅  Made qr_codes.location_address nullable")
                else:
                    print("ℹ️   qr_codes.location_address already nullable — skipped.")

                conn.commit()
        else:
            print("ℹ️   qr_codes.location and location_address already nullable — skipped.")

        # ----------------------------------------------------------------
        # Step 4: Add qr_address column to attendance_data if absent
        # Stores the selected location's address for dynamic QR check-ins
        # ----------------------------------------------------------------
        inspector3 = sa_inspect(db.engine)
        att_cols = {c['name'] for c in inspector3.get_columns('attendance_data')}
        if 'qr_address' not in att_cols:
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE attendance_data ADD COLUMN qr_address TEXT NULL"
                ))
                conn.commit()
            print("\u2705  Added column: attendance_data.qr_address")
        else:
            print("\u2139\ufe0f   Column attendance_data.qr_address already exists \u2014 skipped.")

        print("\nMigration complete.")
        print("All existing QR codes remain fully unaffected (qr_type = 'standard').")


if __name__ == '__main__':
    run_migration()
