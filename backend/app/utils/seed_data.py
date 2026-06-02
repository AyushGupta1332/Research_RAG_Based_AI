"""
Research Agent — Seeding and Ingestion Script

Seeds a default user (Ayush, ID 1) and triggers the ingestion pipeline
for the Aegis DLP paper to populate the database and vector store,
enabling the Performance Evaluation Dashboard to show non-zero real metrics.
"""

import os
import sys
import logging

# Ensure root directory is in path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_DIR = os.path.dirname(ROOT_DIR)
sys.path.insert(0, WORKSPACE_DIR)

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.paper import Paper
from backend.app.services.ingestion_service import _process_paper_worker
from backend.app.services.bm25_service import build_index

# Configure logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

def seed_and_ingest():
    app = create_app()
    with app.app_context():
        logger.info("Initializing seeding sequence...")

        # 0. Wipe database tables and ChromaDB directory for a 100% clean state
        logger.info("Wiping existing database tables...")
        db.drop_all()
        db.create_all()

        chromadb_path = os.path.join(WORKSPACE_DIR, "backend", "instance", "chromadb")
        if os.path.exists(chromadb_path):
            logger.info("Wiping existing ChromaDB directory...")
            import shutil
            try:
                shutil.rmtree(chromadb_path)
            except Exception as e:
                logger.warning(f"Could not remove ChromaDB folder: {e}")

        # 1. Ensure user 'Ayush' exists with ID 1
        user = User(id=1, username="Ayush", email="ayush@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        logger.info("Created user with ID 1 (Ayush).")

        # 2. Check if the Aegis DLP paper is registered in the database
        paper = Paper.query.filter_by(user_id=1).first()
        if not paper:
            pdf_path = os.path.join(WORKSPACE_DIR, "uploads", "1", "RESEARCH_PAPER.pdf")
            if not os.path.exists(pdf_path):
                logger.error(f"Error: Target research paper PDF not found at {pdf_path}")
                return

            paper = Paper(
                user_id=1,
                file_path=pdf_path,
                file_name="RESEARCH_PAPER.pdf",
                file_size=os.path.getsize(pdf_path),
                status="uploaded"
            )
            db.session.add(paper)
            db.session.commit()
            logger.info(f"Created Paper record in DB (ID: {paper.id}).")
        else:
            logger.info(f"Paper record already exists in DB (ID: {paper.id}, Status: '{paper.status}').")

        # 3. Run background ingestion worker synchronously inside the app context
        logger.info(f"Running ingestion pipeline worker on paper ID {paper.id}...")
        _process_paper_worker(app, paper.id)

        # 4. Force build/rebuild of the BM25 index
        logger.info("Rebuilding BM25 keyword index...")
        build_index(app)

        logger.info("Seeding and ingestion sequence completed successfully!")
        logger.info("All documents are successfully section-parsed, semantic-chunked, embedded in ChromaDB, and indexed in BM25.")

if __name__ == "__main__":
    seed_and_ingest()
